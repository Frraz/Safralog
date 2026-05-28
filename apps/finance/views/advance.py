"""
SafraLog — apps/finance/views/advance.py
Views de Adiantamentos ao motorista.
"""

from __future__ import annotations

from django import forms
from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from apps.core.mixins import RoleRequiredMixin, TenantRequiredMixin
from apps.finance.models import Advance
from apps.logistics.models import Driver
from apps.operations.models import Harvest

# ─────────────────────────────────────────────────────────────
# FORM
# ─────────────────────────────────────────────────────────────


class AdvanceForm(forms.ModelForm):
    class Meta:
        model = Advance
        fields = [
            "driver",
            "harvest",
            "amount",
            "payment_date",
            "payment_method",
            "reference_code",
            "notes",
        ]
        widgets = {
            "payment_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "notes": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, tenant=None, **kwargs):
        super().__init__(*args, **kwargs)
        if tenant:
            self.fields["driver"].queryset = Driver.objects.filter(
                tenant=tenant, is_active=True, status="active"
            ).order_by("name")
            self.fields["harvest"].queryset = Harvest.objects.filter(
                tenant=tenant, status="active"
            ).order_by("-start_date")
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "input")
        self.fields["harvest"].required = False
        self.fields["reference_code"].required = False
        self.fields["notes"].required = False


# ─────────────────────────────────────────────────────────────
# LISTAGEM
# ─────────────────────────────────────────────────────────────


class AdvanceListView(TenantRequiredMixin, View):
    template_name = "finance/advance/list.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        advances = (
            Advance.objects.filter(tenant=request.tenant, is_active=True)
            .select_related("driver", "harvest")
            .order_by("-payment_date", "-created_at")[:100]
        )
        return render(request, self.template_name, {"advances": advances})


# ─────────────────────────────────────────────────────────────
# CADASTRO
# ─────────────────────────────────────────────────────────────


class AdvanceCreateView(RoleRequiredMixin, View):
    required_roles = ["admin", "manager"]
    template_name = "finance/advance/form.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        from django.utils import timezone

        return render(
            request,
            self.template_name,
            {
                "form": AdvanceForm(
                    tenant=request.tenant,
                    initial={"payment_date": timezone.localdate()},
                ),
            },
        )

    def post(self, request: HttpRequest) -> HttpResponse:
        form = AdvanceForm(request.POST, tenant=request.tenant)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form})

        advance = form.save(commit=False)
        advance.tenant = request.tenant

        # financial_account é obrigatório — busca da conta do motorista
        driver = advance.driver
        if not driver.financial_account_id:
            messages.error(
                request,
                f"{driver.name} não possui conta financeira. "
                "Cadastre o motorista novamente para criar a conta automaticamente.",
            )
            return render(request, self.template_name, {"form": form})

        advance.financial_account = driver.financial_account
        advance.save()

        # Confirma imediatamente (gera LedgerEntry de DEBIT)
        try:
            advance.confirm()
            messages.success(
                request,
                f"Adiantamento de R$ {advance.amount:.2f} registrado e lançado para {driver.name}.",
            )
        except Exception:
            import logging

            logging.getLogger("safralog").exception(
                "Falha ao confirmar adiantamento no ledger",
                extra={"advance_id": str(advance.pk)},
            )
            messages.warning(
                request,
                "Adiantamento salvo, mas houve falha no lançamento contábil. Contate o suporte.",
            )

        return redirect("finance:advance-list")


# ─────────────────────────────────────────────────────────────
# CANCELAMENTO
# ─────────────────────────────────────────────────────────────


class AdvanceCancelView(RoleRequiredMixin, View):
    required_roles = ["admin", "manager"]

    def post(self, request: HttpRequest, pk) -> HttpResponse:
        advance = get_object_or_404(Advance, pk=pk, tenant=request.tenant, is_active=True)
        try:
            reason = request.POST.get("reason", "")
            advance.cancel(reason=reason)
            messages.success(request, f"Adiantamento de {advance.driver.name} cancelado.")
        except ValueError as e:
            messages.error(request, str(e))

        return redirect("finance:advance-list")


class AdvanceDetailView(TenantRequiredMixin, View):
    template_name = "finance/advance/detail.html"

    def get(self, request: HttpRequest, pk) -> HttpResponse:
        advance = get_object_or_404(
            Advance.objects.select_related("driver", "harvest", "ledger_entry"),
            pk=pk,
            tenant=request.tenant,
            is_active=True,
        )
        return render(
            request,
            self.template_name,
            {
                "advance": advance,
                "can_cancel": (
                    advance.status == Advance.Status.PENDING
                    and request.user.role in ("admin", "manager")
                ),
            },
        )
