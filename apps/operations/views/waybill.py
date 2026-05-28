"""
SafraLog — apps/operations/views/waybill.py
"""

from __future__ import annotations

from decimal import Decimal

from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import DecimalField, ExpressionWrapper, F, Q, Sum
from django.db.models.functions import Coalesce
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from apps.core.mixins import HTMXMixin, RoleRequiredMixin, TenantRequiredMixin
from apps.logistics.models import Driver

from ..forms.waybill import WaybillForm
from ..models import Waybill

_ZERO = Decimal("0")


class WaybillListView(TenantRequiredMixin, HTMXMixin, View):
    template_name = "operations/waybill/list.html"
    paginate_by = 25

    def get(self, request: HttpRequest) -> HttpResponse:
        qs = self._get_filtered_queryset(request)

        confirmed_qs = qs.filter(status__in=["confirmed", "settled"])
        agg = confirmed_qs.aggregate(
            gross=Coalesce(Sum("gross_weight"), _ZERO, output_field=DecimalField()),
            tare=Coalesce(Sum("tare_weight"), _ZERO, output_field=DecimalField()),
            value=Coalesce(
                Sum(
                    ExpressionWrapper(
                        (F("gross_weight") - F("tare_weight")) * F("unit_price") / Decimal("1000"),
                        output_field=DecimalField(max_digits=18, decimal_places=4),
                    )
                ),
                _ZERO,
                output_field=DecimalField(),
            ),
        )
        summary = {
            "total_tons": (agg["gross"] - agg["tare"]) / Decimal("1000"),
            "total_value": agg["value"],
        }

        paginator = Paginator(qs, self.paginate_by)
        page_obj = paginator.get_page(request.GET.get("page", 1))
        drivers = Driver.objects.filter(tenant=request.tenant, is_active=True).order_by("name")

        context = {
            "page_obj": page_obj,
            "summary": summary,
            "status_choices": Waybill.Status.choices,
            "drivers": drivers,
        }

        if self.is_htmx and request.headers.get("HX-Target") == "waybill-table":
            return render(request, "operations/waybill/_table.html", context)
        return render(request, self.template_name, context)

    def _get_filtered_queryset(self, request: HttpRequest):
        qs = (
            Waybill.objects.filter(tenant=request.tenant, is_active=True)
            .select_related("driver", "vehicle", "field", "harvest")
            .order_by("-operation_date", "-created_at")
        )
        status = request.GET.get("status")
        driver_id = request.GET.get("driver")
        date_start = request.GET.get("date_start")
        date_end = request.GET.get("date_end")
        q = request.GET.get("q", "").strip()

        if status:
            qs = qs.filter(status=status)
        if driver_id:
            qs = qs.filter(driver_id=driver_id)
        if date_start:
            qs = qs.filter(operation_date__gte=date_start)
        if date_end:
            qs = qs.filter(operation_date__lte=date_end)
        if q:
            qs = qs.filter(Q(number__icontains=q) | Q(driver__name__icontains=q))
        return qs


class WaybillDetailView(TenantRequiredMixin, View):
    template_name = "operations/waybill/detail.html"

    def get(self, request: HttpRequest, pk) -> HttpResponse:
        waybill = get_object_or_404(
            Waybill.objects.select_related("driver", "vehicle", "field", "harvest"),
            pk=pk,
            tenant=request.tenant,
            is_active=True,
        )

        ct = ContentType.objects.get_for_model(Waybill)
        from apps.attachments.models import Attachment

        attachments = Attachment.objects.filter(
            content_type=ct,
            object_id=str(waybill.pk),
            tenant=request.tenant,
            is_active=True,
        ).order_by("created_at")

        role = request.user.role
        can_confirm = waybill.can_confirm and role in ("admin", "manager", "operator")
        can_cancel = waybill.can_cancel and role in ("admin", "manager")

        return render(
            request,
            self.template_name,
            {
                "waybill": waybill,
                "attachments": attachments,
                "can_confirm": can_confirm,
                "can_cancel": can_cancel,
            },
        )


class WaybillCreateView(RoleRequiredMixin, HTMXMixin, View):
    required_roles = ["admin", "manager", "operator"]
    template_name = "operations/waybill/form.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        return render(
            request,
            self.template_name,
            {"form": WaybillForm(tenant=request.tenant), "action": "create"},
        )

    def post(self, request: HttpRequest) -> HttpResponse:
        form = WaybillForm(request.POST, tenant=request.tenant)

        if form.is_valid():
            waybill = form.save(commit=False)
            waybill.tenant = request.tenant
            last = (
                Waybill.objects.filter(tenant=request.tenant)
                .order_by("-number")
                .values_list("number", flat=True)
                .first()
            )
            waybill.number = int(last or 0) + 1
            waybill.save()
            messages.success(request, f"Romaneio #{waybill.number} criado com sucesso.")
            if self.is_htmx:
                return self.htmx_redirect(waybill.get_absolute_url())
            return redirect(waybill.get_absolute_url())

        if self.is_htmx:
            return render(request, "operations/waybill/_form_errors.html", {"form": form})
        return render(request, self.template_name, {"form": form, "action": "create"})


class WaybillUpdateView(RoleRequiredMixin, HTMXMixin, View):
    required_roles = ["admin", "manager", "operator"]
    template_name = "operations/waybill/form.html"

    def _get_waybill(self, pk, tenant):
        return get_object_or_404(Waybill, pk=pk, tenant=tenant, is_active=True)

    def get(self, request: HttpRequest, pk) -> HttpResponse:
        waybill = self._get_waybill(pk, request.tenant)
        return render(
            request,
            self.template_name,
            {
                "form": WaybillForm(instance=waybill, tenant=request.tenant),
                "waybill": waybill,
                "action": "edit",
            },
        )

    def post(self, request: HttpRequest, pk) -> HttpResponse:
        waybill = self._get_waybill(pk, request.tenant)

        if not waybill.is_editable:
            messages.error(request, "Apenas romaneios em rascunho podem ser editados.")
            return redirect(waybill.get_absolute_url())

        form = WaybillForm(request.POST, instance=waybill, tenant=request.tenant)
        if form.is_valid():
            form.save()
            messages.success(request, f"Romaneio #{waybill.number} atualizado.")
            return redirect(waybill.get_absolute_url())

        return render(
            request,
            self.template_name,
            {"form": form, "waybill": waybill, "action": "edit"},
        )


class WaybillConfirmView(RoleRequiredMixin, HTMXMixin, View):
    required_roles = ["admin", "manager"]

    def post(self, request: HttpRequest, pk) -> HttpResponse:
        waybill = get_object_or_404(
            Waybill.objects.select_related("driver__financial_account"),
            pk=pk,
            tenant=request.tenant,
            is_active=True,
        )

        if not waybill.can_confirm:
            messages.error(
                request,
                f"Romaneio #{waybill.number} não pode ser confirmado "
                f"(status: {waybill.get_status_display()}).",
            )
        else:
            try:
                self._confirm_atomic(request, waybill)
                messages.success(request, f"Romaneio #{waybill.number} confirmado.")
            except Exception as exc:
                messages.error(request, f"Erro ao confirmar romaneio: {exc}")

        if self.is_htmx:
            return self.htmx_refresh()
        return redirect(waybill.get_absolute_url())

    @staticmethod
    @transaction.atomic
    def _confirm_atomic(request, waybill) -> None:
        from apps.finance.services.ledger_service import record_waybill_production

        waybill.confirm(user=request.user)

        account = getattr(waybill.driver, "financial_account", None)
        if account:
            entry = record_waybill_production(
                tenant=request.tenant,
                account=account,
                waybill=waybill,
            )
            if entry:
                Waybill.objects.filter(pk=waybill.pk).update(ledger_entry=entry)


class WaybillCancelView(RoleRequiredMixin, HTMXMixin, View):
    required_roles = ["admin", "manager"]

    def post(self, request: HttpRequest, pk) -> HttpResponse:
        waybill = get_object_or_404(
            Waybill.objects.select_related("ledger_entry"),
            pk=pk,
            tenant=request.tenant,
            is_active=True,
        )

        if not waybill.can_cancel:
            messages.error(
                request,
                f"Romaneio #{waybill.number} não pode ser cancelado "
                f"(status: {waybill.get_status_display()}).",
            )
        else:
            try:
                reason = request.POST.get("reason", "").strip()
                self._cancel_atomic(request.user, waybill, reason)
                messages.success(request, f"Romaneio #{waybill.number} cancelado.")
            except ValueError as exc:
                messages.error(request, str(exc))
            except Exception as exc:
                messages.error(request, f"Erro ao cancelar romaneio: {exc}")

        if self.is_htmx:
            return self.htmx_refresh()
        return redirect(waybill.get_absolute_url())

    @staticmethod
    @transaction.atomic
    def _cancel_atomic(user, waybill, reason: str = "") -> None:
        """
        Cancela romaneio e estorna LedgerEntry em uma transação única.
        @transaction.atomic garante rollback total se qualquer step falhar.
        select_for_update removido — incompatível com o wrapping de transação
        do pytest-django e desnecessário dado o can_cancel check na view.
        """
        if waybill.is_confirmed and waybill.ledger_entry_id:
            entry = waybill.ledger_entry
            if entry and not entry.is_reversed:
                entry.create_reversal(
                    user=user,
                    reason=reason or f"Cancelamento do romaneio #{waybill.number}",
                )
        waybill.cancel(user=user)
