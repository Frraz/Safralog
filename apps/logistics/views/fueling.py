"""
Views de Abastecimentos.
"""

from __future__ import annotations

from django import forms
from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from apps.core.mixins import RoleRequiredMixin, TenantRequiredMixin

from ..models import Driver, Fueling, Vehicle


class FuelingForm(forms.ModelForm):
    class Meta:
        model = Fueling
        fields = [
            "fueling_date",
            "driver",
            "vehicle",
            "harvest",
            "fuel_type",
            "liters",
            "posted_price_per_liter",
            "driver_price_per_liter",
            "extras_amount",
            "payment_method",
            "odometer",
            "station_name",
            "notes",
        ]
        widgets = {
            "fueling_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "notes": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, tenant=None, **kwargs):
        super().__init__(*args, **kwargs)
        if tenant:
            self.fields["driver"].queryset = Driver.objects.filter(
                tenant=tenant, is_active=True, status="active"
            ).order_by("name")
            self.fields["vehicle"].queryset = Vehicle.objects.filter(
                tenant=tenant, is_active=True
            ).order_by("plate")
            from apps.operations.models import Harvest
            self.fields["harvest"].queryset = Harvest.objects.filter(
                tenant=tenant, is_active=True, status="active"
            )
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "input")
        self.fields["driver"].required = False
        self.fields["harvest"].required = False
        self.fields["vehicle"].required = False
        self.fields["posted_price_per_liter"].required = False
        self.fields["extras_amount"].required = False
        self.fields["odometer"].required = False
        self.fields["station_name"].required = False
        self.fields["notes"].required = False
        self.fields["posted_price_per_liter"].label = "Preço do posto (R$/L) — opcional"
        self.fields["driver_price_per_liter"].label = "Preço descontado do motorista (R$/L) *"
        self.fields["extras_amount"].label = "Outros produtos no cupom (R$)"


class FuelingListView(TenantRequiredMixin, View):
    template_name = "logistics/fueling/list.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        qs = (
            Fueling.objects.filter(tenant=request.tenant, is_active=True)
            .select_related("driver", "vehicle")
            .order_by("-fueling_date", "-created_at")
        )
        driver_id = request.GET.get("driver", "")
        if driver_id:
            qs = qs.filter(driver_id=driver_id)

        drivers = Driver.objects.filter(tenant=request.tenant, is_active=True).order_by("name")
        return render(
            request,
            self.template_name,
            {
                "fuelings": qs[:50],
                "drivers": drivers,
                "driver_filter": driver_id,
            },
        )


class FuelingDetailView(TenantRequiredMixin, View):
    def get(self, request: HttpRequest, pk) -> HttpResponse:
        fueling = get_object_or_404(
            Fueling.objects.select_related("driver", "vehicle"),
            pk=pk,
            tenant=request.tenant,
            is_active=True,
        )
        return render(request, "logistics/fueling/detail.html", {"fueling": fueling})


class FuelingCreateView(RoleRequiredMixin, View):
    required_roles = ["admin", "manager", "operator"]
    template_name = "logistics/fueling/form.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        from django.utils import timezone

        form = FuelingForm(
            tenant=request.tenant,
            initial={"fueling_date": timezone.localdate()},
        )
        return render(request, self.template_name, {"form": form, "action": "create"})

    def post(self, request: HttpRequest) -> HttpResponse:
        form = FuelingForm(request.POST, tenant=request.tenant)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form, "action": "create"})

        fueling = form.save(commit=False)
        fueling.tenant = request.tenant
        fueling.save()

        # Débito no ledger se o motorista tiver conta financeira
        if fueling.driver and fueling.driver.financial_account_id:
            try:
                from apps.finance.services.ledger_service import record_fueling_debit

                record_fueling_debit(
                    tenant=request.tenant,
                    account=fueling.driver.financial_account,
                    fueling=fueling,
                )
            except Exception:
                # Não bloqueia o cadastro por falha no ledger — loga e segue
                import logging

                logging.getLogger("safralog").exception(
                    "Falha ao registrar débito de abastecimento no ledger",
                    extra={"fueling_id": str(fueling.pk)},
                )

        messages.success(
            request,
            f"Abastecimento registrado: {fueling.liters:.1f} L — "
            f"{fueling.vehicle.plate}"
            f"{' / ' + fueling.driver.name if fueling.driver else ''}.",
        )
        return redirect("logistics:fueling-list")


class FuelingUpdateView(RoleRequiredMixin, View):
    """
    Edição de abastecimento.
    Só permitida para registros recentes — ledger não é alterado,
    apenas os dados do Fueling. Para correção de valor, use ajuste manual.
    """

    required_roles = ["admin", "manager"]
    template_name = "logistics/fueling/form.html"

    def get(self, request: HttpRequest, pk) -> HttpResponse:
        fueling = get_object_or_404(
            Fueling.objects.select_related("driver", "vehicle"),
            pk=pk,
            tenant=request.tenant,
            is_active=True,
        )
        form = FuelingForm(instance=fueling, tenant=request.tenant)
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "fueling": fueling,
                "action": "edit",
            },
        )

    def post(self, request: HttpRequest, pk) -> HttpResponse:
        fueling = get_object_or_404(
            Fueling.objects.select_related("driver", "vehicle"),
            pk=pk,
            tenant=request.tenant,
            is_active=True,
        )
        form = FuelingForm(request.POST, instance=fueling, tenant=request.tenant)
        if not form.is_valid():
            return render(
                request,
                self.template_name,
                {
                    "form": form,
                    "fueling": fueling,
                    "action": "edit",
                },
            )

        form.save()
        messages.success(
            request, f"Abastecimento atualizado: {fueling.liters:.1f} L — {fueling.vehicle.plate}."
        )
        return redirect("logistics:fueling-detail", pk=fueling.pk)
