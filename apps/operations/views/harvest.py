"""
SafraLog — apps/operations/views/harvest.py
Views de Safras (Harvest).
"""

from __future__ import annotations

from django import forms
from django.contrib import messages
from django.db import transaction
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from apps.core.mixins import RoleRequiredMixin, TenantRequiredMixin

from ..models import Harvest, Waybill

# ── Form ──────────────────────────────────────────────────────────────────────


class HarvestForm(forms.ModelForm):
    class Meta:
        model = Harvest
        fields = [
            "name",
            "crop_type",
            "status",
            "start_date",
            "end_date",
            "expected_area_ha",
            "expected_yield_ton_ha",
            "notes",
        ]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "end_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "input")
        self.fields["end_date"].required = False
        self.fields["expected_area_ha"].required = False
        self.fields["expected_yield_ton_ha"].required = False
        self.fields["notes"].required = False


# ── Helper ────────────────────────────────────────────────────────────────────


def _ensure_single_active(tenant, new_status: str, exclude_pk=None) -> int:
    """
    Se new_status == 'active', conclui automaticamente qualquer outra safra
    ativa do mesmo tenant, evitando o IntegrityError da constraint
    unique_active_harvest_per_tenant.

    Retorna o número de safras concluídas automaticamente.
    Deve ser chamado DENTRO de um transaction.atomic() já aberto.
    """
    if new_status != "active":
        return 0

    qs = Harvest.objects.filter(tenant=tenant, status="active")
    if exclude_pk is not None:
        qs = qs.exclude(pk=exclude_pk)

    count = qs.count()
    if count:
        qs.update(status="completed")

    return count


# ── Views ─────────────────────────────────────────────────────────────────────


class HarvestListView(TenantRequiredMixin, View):
    template_name = "operations/harvest/list.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        harvests = Harvest.objects.filter(tenant=request.tenant).order_by("-start_date")
        return render(request, self.template_name, {"harvests": harvests})


class HarvestDetailView(TenantRequiredMixin, View):
    template_name = "operations/harvest/detail.html"

    def get(self, request: HttpRequest, pk) -> HttpResponse:
        harvest = get_object_or_404(Harvest, pk=pk, tenant=request.tenant)
        fields = harvest.fields.filter(is_active=True).order_by("name")
        waybill_count = Waybill.objects.filter(tenant=request.tenant, harvest=harvest).count()
        return render(
            request,
            self.template_name,
            {
                "harvest": harvest,
                "fields": fields,
                "waybill_count": waybill_count,
            },
        )


class HarvestCreateView(RoleRequiredMixin, View):
    required_roles = ["admin", "manager"]
    template_name = "operations/harvest/form.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        return render(
            request,
            self.template_name,
            {"form": HarvestForm(), "action": "create"},
        )

    def post(self, request: HttpRequest) -> HttpResponse:
        form = HarvestForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                replaced = _ensure_single_active(
                    tenant=request.tenant,
                    new_status=form.cleaned_data.get("status"),
                )
                harvest = form.save(commit=False)
                harvest.tenant = request.tenant
                harvest.save()

            messages.success(request, f"Safra '{harvest.name}' criada com sucesso.")
            if replaced:
                messages.info(
                    request,
                    "A safra anterior foi automaticamente concluída.",
                )
            return redirect("operations:harvest-detail", pk=harvest.pk)

        return render(
            request,
            self.template_name,
            {"form": form, "action": "create"},
        )


class HarvestUpdateView(RoleRequiredMixin, View):
    required_roles = ["admin", "manager"]
    template_name = "operations/harvest/form.html"

    def get(self, request: HttpRequest, pk) -> HttpResponse:
        harvest = get_object_or_404(Harvest, pk=pk, tenant=request.tenant)
        return render(
            request,
            self.template_name,
            {
                "form": HarvestForm(instance=harvest),
                "harvest": harvest,
                "action": "edit",
            },
        )

    def post(self, request: HttpRequest, pk) -> HttpResponse:
        harvest = get_object_or_404(Harvest, pk=pk, tenant=request.tenant)
        form = HarvestForm(request.POST, instance=harvest)

        if form.is_valid():
            with transaction.atomic():
                # Garante que apenas esta safra fique 'active',
                # concluindo automaticamente qualquer outra ativa.
                replaced = _ensure_single_active(
                    tenant=request.tenant,
                    new_status=form.cleaned_data.get("status"),
                    exclude_pk=pk,  # ← exclui a própria safra sendo editada
                )
                form.save()

            messages.success(request, f"Safra '{harvest.name}' atualizada.")
            if replaced:
                messages.info(
                    request,
                    "A safra anteriormente ativa foi automaticamente concluída.",
                )
            return redirect("operations:harvest-detail", pk=harvest.pk)

        return render(
            request,
            self.template_name,
            {"form": form, "harvest": harvest, "action": "edit"},
        )
