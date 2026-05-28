"""
SafraLog — apps/logistics/views/proprietario.py
Views de Proprietários de Caminhões.
"""
from __future__ import annotations

from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from apps.core.mixins import HTMXMixin, RoleRequiredMixin, TenantRequiredMixin

from ..forms.proprietario import ProprietarioForm
from ..models import Proprietario


class ProprietarioListView(TenantRequiredMixin, View):
    template_name = "logistics/proprietario/list.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        proprietarios = (
            Proprietario.objects.filter(tenant=request.tenant, is_active=True)
            .select_related("driver", "financial_account")
            .prefetch_related("vehicles")
            .order_by("name")
        )
        return render(request, self.template_name, {"proprietarios": proprietarios})


class ProprietarioDetailView(TenantRequiredMixin, View):
    template_name = "logistics/proprietario/detail.html"

    def get(self, request: HttpRequest, pk) -> HttpResponse:
        prop = get_object_or_404(
            Proprietario.objects.select_related("driver", "financial_account"),
            pk=pk,
            tenant=request.tenant,
            is_active=True,
        )
        vehicles = prop.vehicles.filter(is_active=True).order_by("plate")
        balance = prop.financial_account.current_balance if prop.financial_account_id else None

        return render(
            request,
            self.template_name,
            {
                "prop": prop,
                "vehicles": vehicles,
                "balance": balance,
                "can_edit": request.user.role in ("admin", "manager"),
            },
        )


class ProprietarioCreateView(RoleRequiredMixin, HTMXMixin, View):
    required_roles = ["admin", "manager"]
    template_name = "logistics/proprietario/form.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        form = ProprietarioForm(tenant=request.tenant)
        return render(request, self.template_name, {"form": form, "action": "create"})

    def post(self, request: HttpRequest) -> HttpResponse:
        form = ProprietarioForm(request.POST, tenant=request.tenant)

        if not form.is_valid():
            return render(request, self.template_name, {"form": form, "action": "create"})

        prop = form.save(commit=False)
        prop.tenant = request.tenant
        prop.save()  # save() auto-cria FinancialAccount

        messages.success(request, f"Proprietário {prop.name} cadastrado com sucesso.")

        if self.is_htmx:
            return self.htmx_redirect(redirect("logistics:proprietario-detail", pk=prop.pk)["Location"])
        return redirect("logistics:proprietario-detail", pk=prop.pk)


class ProprietarioUpdateView(RoleRequiredMixin, HTMXMixin, View):
    required_roles = ["admin", "manager"]
    template_name = "logistics/proprietario/form.html"

    def get(self, request: HttpRequest, pk) -> HttpResponse:
        prop = get_object_or_404(Proprietario, pk=pk, tenant=request.tenant, is_active=True)
        form = ProprietarioForm(instance=prop, tenant=request.tenant)
        return render(request, self.template_name, {"form": form, "prop": prop, "action": "edit"})

    def post(self, request: HttpRequest, pk) -> HttpResponse:
        prop = get_object_or_404(Proprietario, pk=pk, tenant=request.tenant, is_active=True)
        form = ProprietarioForm(request.POST, instance=prop, tenant=request.tenant)

        if not form.is_valid():
            return render(request, self.template_name, {"form": form, "prop": prop, "action": "edit"})

        form.save()
        messages.success(request, f"Proprietário {prop.name} atualizado.")

        if self.is_htmx:
            return self.htmx_redirect(redirect("logistics:proprietario-detail", pk=prop.pk)["Location"])
        return redirect("logistics:proprietario-detail", pk=prop.pk)


class ProprietarioDeactivateView(RoleRequiredMixin, HTMXMixin, View):
    required_roles = ["admin", "manager"]

    def post(self, request: HttpRequest, pk) -> HttpResponse:
        prop = get_object_or_404(Proprietario, pk=pk, tenant=request.tenant, is_active=True)

        veiculos_ativos = prop.vehicles.filter(is_active=True).count()
        if veiculos_ativos:
            messages.error(
                request,
                f"{prop.name} possui {veiculos_ativos} veículo(s) ativo(s). "
                "Inative ou desvinculue os veículos antes de inativar o proprietário.",
            )
            if self.is_htmx:
                return self.htmx_refresh()
            return redirect("logistics:proprietario-detail", pk=prop.pk)

        prop.soft_delete()
        messages.success(request, f"Proprietário {prop.name} inativado.")

        if self.is_htmx:
            return self.htmx_redirect(redirect("logistics:proprietario-list")["Location"])
        return redirect("logistics:proprietario-list")
