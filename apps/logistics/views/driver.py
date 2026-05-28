"""
SafraLog — apps/logistics/views/driver.py
Views de Motoristas.
"""

from __future__ import annotations

from decimal import Decimal

from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.db.models import Count, DecimalField, ExpressionWrapper, F, Q, Sum
from django.db.models.functions import Coalesce
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View

from apps.core.mixins import HTMXMixin, RoleRequiredMixin, TenantRequiredMixin
from apps.finance.models import FinancialAccount
from apps.logistics.models import Fueling
from apps.operations.models import Waybill

from ..forms.driver import DriverForm
from ..models import Driver

_ZERO = Decimal("0")

# ─────────────────────────────────────────────────────────────
# HELPER
# ─────────────────────────────────────────────────────────────


def _criar_conta_financeira(tenant, driver: Driver) -> FinancialAccount:
    """
    Cria e vincula conta financeira ao motorista.
    Usa linked_type + linked_id (campos reais do GenericFK no FinancialAccount).
    NÃO usar 'content_object' diretamente no objects.create() —
    o atalho GenericFK não funciona como kwarg do construtor.
    """
    account = FinancialAccount.objects.create(
        tenant=tenant,
        name=f"Conta — {driver.name}",
        account_type=FinancialAccount.AccountType.DRIVER,
        linked_type=ContentType.objects.get_for_model(Driver),
        linked_id=driver.pk,
    )
    Driver.objects.filter(pk=driver.pk).update(financial_account=account)
    driver.financial_account = account
    return account


# ─────────────────────────────────────────────────────────────
# LISTAGEM
# ─────────────────────────────────────────────────────────────


class DriverListView(TenantRequiredMixin, View):
    template_name = "logistics/driver/list.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        today = timezone.localdate()
        month_start = today.replace(day=1)

        drivers = (
            Driver.objects.filter(tenant=request.tenant, is_active=True)
            .select_related("financial_account")
            .annotate(
                month_waybills=Count(
                    "waybills",
                    filter=Q(
                        waybills__is_active=True,
                        waybills__status__in=["confirmed", "settled"],
                        waybills__operation_date__gte=month_start,
                    ),
                ),
                month_fuel_liters=Coalesce(
                    Sum(
                        "fuelings__liters",
                        filter=Q(
                            fuelings__is_active=True,
                            fuelings__fueling_date__gte=month_start,
                        ),
                    ),
                    _ZERO,
                    output_field=DecimalField(),
                ),
            )
            .order_by("name")
        )

        return render(
            request,
            self.template_name,
            {
                "drivers": drivers,
                "month_start": month_start,
            },
        )


# ─────────────────────────────────────────────────────────────
# DETALHE
# ─────────────────────────────────────────────────────────────


class DriverDetailView(TenantRequiredMixin, View):
    template_name = "logistics/driver/detail.html"

    def get(self, request: HttpRequest, pk) -> HttpResponse:
        driver = get_object_or_404(
            Driver.objects.select_related("financial_account", "tenant"),
            pk=pk,
            tenant=request.tenant,
            is_active=True,
        )

        recent_waybills = (
            Waybill.objects.filter(tenant=request.tenant, driver=driver, is_active=True)
            .select_related("harvest", "field", "vehicle")
            .order_by("-operation_date", "-created_at")[:10]
        )

        recent_fuelings = (
            Fueling.objects.filter(tenant=request.tenant, driver=driver, is_active=True)
            .select_related("vehicle", "harvest")
            .order_by("-fueling_date")[:8]
        )

        today = timezone.localdate()
        month_start = today.replace(day=1)

        # ── Waybill stats ──────────────────────────────────────────────────
        # FIX: Coalesce fallback deve ser Decimal("0"), não int 0.
        # Misturar DecimalField (Sum) com IntegerField (literal 0) causa
        # FieldError: "Expression contains mixed types".
        waybill_stats = Waybill.objects.filter(
            tenant=request.tenant,
            driver=driver,
            is_active=True,
            status__in=["confirmed", "settled"],
            operation_date__gte=month_start,
        ).aggregate(
            month_waybills=Count("id"),
            month_gross=Coalesce(Sum("gross_weight"), _ZERO, output_field=DecimalField()),
            month_tare=Coalesce(Sum("tare_weight"), _ZERO, output_field=DecimalField()),
        )
        # Divisão por Decimal("1000") mantém precisão; evita truncamento inteiro.
        waybill_stats["month_net_tons"] = (
            waybill_stats["month_gross"] - waybill_stats["month_tare"]
        ) / Decimal("1000")

        # ── Fuel stats ─────────────────────────────────────────────────────
        fuel_stats = Fueling.objects.filter(
            tenant=request.tenant,
            driver=driver,
            is_active=True,
            fueling_date__gte=month_start,
        ).aggregate(
            month_fuel_liters=Coalesce(Sum("liters"), _ZERO, output_field=DecimalField()),
            month_fuel_value=Coalesce(
                Sum(
                    ExpressionWrapper(
                        F("liters") * F("driver_price_per_liter"),
                        output_field=DecimalField(max_digits=12, decimal_places=2),
                    )
                ),
                _ZERO,
                output_field=DecimalField(),
            ),
        )

        balance = driver.financial_account.current_balance if driver.financial_account_id else None

        return render(
            request,
            self.template_name,
            {
                "driver": driver,
                "recent_waybills": recent_waybills,
                "recent_fuelings": recent_fuelings,
                "balance": balance,
                "stats": {**waybill_stats, **fuel_stats},
                "can_edit": request.user.role in ("admin", "manager"),
            },
        )


# ─────────────────────────────────────────────────────────────
# CADASTRO
# ─────────────────────────────────────────────────────────────


class DriverCreateView(RoleRequiredMixin, HTMXMixin, View):
    required_roles = ["admin", "manager"]
    template_name = "logistics/driver/form.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        return render(
            request,
            self.template_name,
            {"form": DriverForm(), "action": "create"},
        )

    def post(self, request: HttpRequest) -> HttpResponse:
        form = DriverForm(request.POST, request.FILES)

        if not form.is_valid():
            return render(
                request,
                self.template_name,
                {"form": form, "action": "create"},
            )

        driver = form.save(commit=False)
        driver.tenant = request.tenant
        driver.save()

        _criar_conta_financeira(request.tenant, driver)

        messages.success(request, f"Motorista {driver.name} cadastrado com sucesso.")

        if self.is_htmx:
            return self.htmx_redirect(redirect("logistics:driver-detail", pk=driver.pk)["Location"])
        return redirect("logistics:driver-detail", pk=driver.pk)


# ─────────────────────────────────────────────────────────────
# EDIÇÃO
# ─────────────────────────────────────────────────────────────


class DriverUpdateView(RoleRequiredMixin, HTMXMixin, View):
    required_roles = ["admin", "manager"]
    template_name = "logistics/driver/form.html"

    def get(self, request: HttpRequest, pk) -> HttpResponse:
        driver = get_object_or_404(Driver, pk=pk, tenant=request.tenant, is_active=True)
        return render(
            request,
            self.template_name,
            {"form": DriverForm(instance=driver), "driver": driver, "action": "edit"},
        )

    def post(self, request: HttpRequest, pk) -> HttpResponse:
        driver = get_object_or_404(Driver, pk=pk, tenant=request.tenant, is_active=True)
        form = DriverForm(request.POST, request.FILES, instance=driver)

        if not form.is_valid():
            return render(
                request,
                self.template_name,
                {"form": form, "driver": driver, "action": "edit"},
            )

        form.save()
        messages.success(request, f"Motorista {driver.name} atualizado.")

        if self.is_htmx:
            return self.htmx_redirect(redirect("logistics:driver-detail", pk=driver.pk)["Location"])
        return redirect("logistics:driver-detail", pk=driver.pk)


# ─────────────────────────────────────────────────────────────
# INATIVAÇÃO (soft delete)
# ─────────────────────────────────────────────────────────────


class DriverDeactivateView(RoleRequiredMixin, HTMXMixin, View):
    required_roles = ["admin", "manager"]

    def post(self, request: HttpRequest, pk) -> HttpResponse:
        driver = get_object_or_404(Driver, pk=pk, tenant=request.tenant, is_active=True)

        romaneios_abertos = Waybill.objects.filter(
            tenant=request.tenant,
            driver=driver,
            status__in=["draft", "confirmed"],
            is_active=True,
        ).count()

        if romaneios_abertos:
            messages.error(
                request,
                f"{driver.name} possui {romaneios_abertos} romaneio(s) em aberto. "
                "Finalize ou cancele-os antes de inativar o motorista.",
            )
            if self.is_htmx:
                return self.htmx_refresh()
            return redirect("logistics:driver-detail", pk=driver.pk)

        driver.soft_delete()
        messages.success(request, f"Motorista {driver.name} inativado.")

        if self.is_htmx:
            return self.htmx_redirect(redirect("logistics:driver-list")["Location"])
        return redirect("logistics:driver-list")
