"""
SafraLog — apps/finance/views/settlement.py
Views de Fechamentos (Settlement).
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View

from apps.core.mixins import RoleRequiredMixin, TenantRequiredMixin
from apps.finance.models import Settlement


class SettlementListView(TenantRequiredMixin, View):
    template_name = "finance/settlement/list.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        settlements = (
            Settlement.objects.filter(tenant=request.tenant, is_active=True)
            .select_related("account", "approved_by")
            .order_by("-period_end")
        )
        return render(request, self.template_name, {"settlements": settlements})


class SettlementDetailView(TenantRequiredMixin, View):
    template_name = "finance/settlement/detail.html"

    def get(self, request: HttpRequest, pk) -> HttpResponse:
        settlement = get_object_or_404(
            Settlement.objects.select_related("account", "approved_by"),
            pk=pk,
            tenant=request.tenant,
            is_active=True,
        )
        ledger_entries = settlement.ledger_entries.filter(is_active=True).order_by(
            "competence_date"
        )
        role = request.user.role
        is_manager = role in ("admin", "manager")
        snap = settlement.snapshot_data or {}
        return render(
            request,
            self.template_name,
            {
                "settlement": settlement,
                "ledger_entries": ledger_entries,
                "snap": snap,
                "today": timezone.localdate(),
                "custom_overrides": settlement.custom_overrides or {},
                "can_submit": is_manager and settlement.status == Settlement.Status.DRAFT,
                "can_approve": is_manager and settlement.status == Settlement.Status.PENDING_APPROVAL,
                "can_close": is_manager and settlement.status == Settlement.Status.APPROVED,
                "can_pay": is_manager and settlement.can_be_paid(),
                "can_override": is_manager and settlement.is_editable,
                "can_cancel": (
                    is_manager
                    and settlement.status not in (
                        Settlement.Status.PAID,
                        Settlement.Status.CLOSED,
                        Settlement.Status.CANCELLED,
                    )
                ),
            },
        )


class SettlementCreateView(RoleRequiredMixin, View):
    required_roles = ["admin", "manager"]
    template_name = "finance/settlement/form.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        from django.utils import timezone

        from apps.logistics.models import Driver

        drivers = Driver.objects.filter(
            tenant=request.tenant, is_active=True, status="active"
        ).order_by("name")
        return render(
            request,
            self.template_name,
            {
                "drivers": drivers,
                "default_period_end": timezone.localdate(),
            },
        )

    def post(self, request: HttpRequest) -> HttpResponse:
        from datetime import date

        from apps.finance.services import settlement_service
        from apps.logistics.models import Driver

        driver_id = request.POST.get("driver")
        period_start_str = request.POST.get("period_start")
        period_end_str = request.POST.get("period_end")

        try:
            driver = Driver.objects.get(pk=driver_id, tenant=request.tenant)
            period_start = date.fromisoformat(period_start_str)
            period_end = date.fromisoformat(period_end_str)
        except (Driver.DoesNotExist, ValueError, TypeError):
            messages.error(request, "Dados inválidos. Verifique os campos.")
            return redirect("finance:settlement-create")

        if period_start > period_end:
            messages.error(request, "A data de início não pode ser posterior ao fim do período.")
            return redirect("finance:settlement-create")

        try:
            settlement = settlement_service.create_settlement(
                tenant=request.tenant,
                driver=driver,
                period_start=period_start,
                period_end=period_end,
                created_by=request.user,
            )
            messages.success(request, f"Acerto criado para {driver.name}.")
            return redirect("finance:settlement-detail", pk=settlement.pk)
        except ValueError as e:
            messages.error(request, str(e))
            return redirect("finance:settlement-create")
        except Exception as e:
            messages.error(request, f"Erro ao criar acerto: {e}")
            return redirect("finance:settlement-create")


class SettlementSubmitView(RoleRequiredMixin, View):
    """DRAFT → PENDING_APPROVAL."""

    required_roles = ["admin", "manager"]

    def post(self, request: HttpRequest, pk) -> HttpResponse:
        settlement = get_object_or_404(
            Settlement,
            pk=pk,
            tenant=request.tenant,
            is_active=True,
            status=Settlement.Status.DRAFT,
        )
        try:
            from apps.finance.services.settlement_service import submit_settlement

            submit_settlement(settlement=settlement)
            messages.success(
                request,
                f"Acerto de {settlement.account.name} enviado para aprovação.",
            )
        except ValueError as e:
            messages.error(request, str(e))
        return redirect("finance:settlement-detail", pk=settlement.pk)


class SettlementApproveView(RoleRequiredMixin, View):
    """PENDING_APPROVAL → APPROVED."""

    required_roles = ["admin", "manager"]

    def post(self, request: HttpRequest, pk) -> HttpResponse:
        settlement = get_object_or_404(
            Settlement,
            pk=pk,
            tenant=request.tenant,
            is_active=True,
            status=Settlement.Status.PENDING_APPROVAL,
        )
        try:
            from apps.finance.services.settlement_service import approve_settlement

            approve_settlement(settlement=settlement, approved_by=request.user)
            messages.success(
                request,
                f"Acerto de {settlement.account.name} aprovado.",
            )
        except ValueError as e:
            messages.error(request, str(e))
        return redirect("finance:settlement-detail", pk=settlement.pk)


class SettlementCloseView(RoleRequiredMixin, View):
    """APPROVED → CLOSED."""

    required_roles = ["admin", "manager"]

    def post(self, request: HttpRequest, pk) -> HttpResponse:
        settlement = get_object_or_404(
            Settlement,
            pk=pk,
            tenant=request.tenant,
            is_active=True,
            status=Settlement.Status.APPROVED,
        )
        try:
            from apps.finance.services.settlement_service import close_settlement

            close_settlement(settlement=settlement, closed_by=request.user)
            messages.success(
                request,
                f"Acerto de {settlement.account.name} fechado com sucesso.",
            )
        except ValueError as e:
            messages.error(request, str(e))
        return redirect("finance:settlement-detail", pk=settlement.pk)


class SettlementCancelView(RoleRequiredMixin, View):
    required_roles = ["admin", "manager"]

    def post(self, request: HttpRequest, pk) -> HttpResponse:
        settlement = get_object_or_404(
            Settlement,
            pk=pk,
            tenant=request.tenant,
            is_active=True,
        )
        try:
            from apps.finance.services.settlement_service import cancel_settlement

            cancel_settlement(settlement=settlement)
            messages.success(
                request,
                f"Acerto de {settlement.account.name} cancelado. "
                "Romaneios revertidos para 'Confirmado'.",
            )
        except ValueError as e:
            messages.error(request, str(e))
        return redirect("finance:settlement-list")


class SettlementMarkPaidView(RoleRequiredMixin, View):
    """
    Marca o fechamento como PAGO e registra o comprovante.

    Recebe: payment_date, payment_notes, payment_proof (arquivo)
    Aceita qualquer fechamento que não seja já PAGO, FECHADO ou CANCELADO.
    """

    required_roles = ["admin", "manager"]

    def post(self, request: HttpRequest, pk) -> HttpResponse:
        settlement = get_object_or_404(
            Settlement,
            pk=pk,
            tenant=request.tenant,
            is_active=True,
        )

        if not settlement.can_be_paid():
            messages.error(
                request,
                f"Acerto com status '{settlement.get_status_display()}' não pode ser marcado como pago.",
            )
            return redirect("finance:settlement-detail", pk=settlement.pk)

        payment_date_str = request.POST.get("payment_date", "")
        payment_notes = request.POST.get("payment_notes", "").strip()
        payment_proof = request.FILES.get("payment_proof")

        # Data de pagamento (obrigatória)
        try:
            from datetime import date
            payment_date = date.fromisoformat(payment_date_str) if payment_date_str else timezone.localdate()
        except ValueError:
            payment_date = timezone.localdate()

        update_fields = [
            "status", "payment_date", "payment_notes", "paid_at", "paid_by", "updated_at"
        ]

        settlement.status = Settlement.Status.PAID
        settlement.payment_date = payment_date
        settlement.payment_notes = payment_notes
        settlement.paid_at = timezone.now()
        settlement.paid_by = request.user

        if payment_proof:
            settlement.payment_proof = payment_proof
            update_fields.append("payment_proof")

        settlement.save(update_fields=update_fields)

        messages.success(
            request,
            f"Acerto de {settlement.account.name} marcado como PAGO em {payment_date.strftime('%d/%m/%Y')}.",
        )
        return redirect("finance:settlement-detail", pk=settlement.pk)


class SettlementOverrideValueView(RoleRequiredMixin, View):
    """
    Salva ou remove um override de valor em custom_overrides.

    Payload JSON: { "category": "waybills"|"fuelings"|"advances",
                    "object_id": "<uuid>",
                    "field": "custom_value"|"custom_debit",
                    "value": 1200.00 | null,
                    "note": "..." }

    Retorna JSON: { "ok": true, "override": {...} }
    """

    required_roles = ["admin", "manager"]

    def post(self, request: HttpRequest, pk) -> JsonResponse:
        import json

        settlement = get_object_or_404(
            Settlement,
            pk=pk,
            tenant=request.tenant,
            is_active=True,
        )

        if not settlement.is_editable:
            return JsonResponse(
                {"ok": False, "error": "Fechamento não pode ser editado no status atual."},
                status=400,
            )

        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return JsonResponse({"ok": False, "error": "JSON inválido."}, status=400)

        category = data.get("category")
        object_id = str(data.get("object_id", ""))
        field = data.get("field")
        value = data.get("value")
        note = data.get("note", "")

        if category not in ("waybills", "fuelings", "advances") or not object_id or not field:
            return JsonResponse({"ok": False, "error": "Parâmetros inválidos."}, status=400)

        overrides = settlement.custom_overrides or {}
        if category not in overrides:
            overrides[category] = {}

        if value is None:
            # Remove o override
            overrides[category].pop(object_id, None)
        else:
            try:
                validated = float(Decimal(str(value)))
            except (InvalidOperation, ValueError):
                return JsonResponse({"ok": False, "error": "Valor inválido."}, status=400)
            overrides[category][object_id] = {field: validated, "note": note}

        settlement.custom_overrides = overrides
        settlement.save(update_fields=["custom_overrides", "updated_at"])

        return JsonResponse({
            "ok": True,
            "override": overrides.get(category, {}).get(object_id, {}),
        })
