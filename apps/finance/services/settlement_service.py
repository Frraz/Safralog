"""
SafraLog — apps/finance/services/settlement_service.py

Serviço de fechamento financeiro de motorista.

Fluxo:
  1. create_settlement() — coleta romaneios, calcula, gera snapshot → DRAFT
  2. submit_settlement() — DRAFT → PENDING_APPROVAL
  3. approve_settlement() — PENDING_APPROVAL → APPROVED (preenche approved_by/at)
  4. close_settlement()  — APPROVED → CLOSED (preenche closed_at)
  5. cancel_settlement() — qualquer status exceto CLOSED → CANCELLED

Princípio: fechamento CONGELA os dados. Após CLOSED,
nada é alterado retroativamente — usa snapshot_data (JSON).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.db import transaction
from django.utils import timezone


@transaction.atomic
def create_settlement(
    *,
    tenant,
    driver,
    period_start: date,
    period_end: date,
    created_by=None,
    vehicle=None,
):
    """
    Cria um fechamento DRAFT para o motorista no período informado.

    Raises:
        ValueError — se não houver romaneios confirmados no período
        ValueError — se já existir fechamento aberto para o mesmo período
    """
    from apps.finance.models import Advance, LedgerEntry, Settlement
    from apps.logistics.models import Fueling
    from apps.operations.models import Waybill

    # Determinar conta do fechamento: proprietário do veículo > motorista
    proprietario = None
    settlement_account = None

    if vehicle is not None and getattr(vehicle, "proprietario_id", None):
        proprietario = vehicle.proprietario if hasattr(vehicle, "proprietario") else None
        if proprietario is None:
            from apps.logistics.models import Proprietario as Prop
            try:
                proprietario = Prop.objects.select_related("financial_account").get(
                    pk=vehicle.proprietario_id
                )
            except Prop.DoesNotExist:
                pass
        if proprietario and proprietario.financial_account_id:
            settlement_account = proprietario.financial_account

    if settlement_account is None:
        # Fallback: usar conta do motorista (comportamento anterior)
        if not driver.financial_account_id:
            raise ValueError(f"Motorista {driver.name} não possui conta financeira.")
        settlement_account = driver.financial_account

    existing = (
        Settlement.objects.filter(
            tenant=tenant,
            account=settlement_account,
            period_start=period_start,
            period_end=period_end,
            is_active=True,
        )
        .exclude(status=Settlement.Status.CANCELLED)
        .first()
    )
    if existing:
        nome = proprietario.name if proprietario else driver.name
        raise ValueError(
            f"Já existe um fechamento para {nome} "
            f"no período {period_start:%d/%m/%Y} → {period_end:%d/%m/%Y}."
        )

    waybill_filter = {
        "tenant": tenant,
        "driver": driver,
        "is_active": True,
        "status": Waybill.Status.CONFIRMED,
        "operation_date__gte": period_start,
        "operation_date__lte": period_end,
    }
    if vehicle is not None:
        waybill_filter["vehicle"] = vehicle

    waybills = list(
        Waybill.objects.filter(**waybill_filter)
        .select_related("field", "vehicle", "harvest")
        .order_by("operation_date")
    )
    if not waybills:
        nome = proprietario.name if proprietario else driver.name
        raise ValueError(
            f"Nenhum romaneio confirmado encontrado para {nome} "
            f"entre {period_start:%d/%m/%Y} e {period_end:%d/%m/%Y}."
        )

    fueling_filter = {
        "tenant": tenant,
        "driver": driver,
        "is_active": True,
        "fueling_date__gte": period_start,
        "fueling_date__lte": period_end,
    }
    if vehicle is not None:
        fueling_filter["vehicle"] = vehicle

    fuelings = list(
        Fueling.objects.filter(**fueling_filter)
        .select_related("vehicle")
        .order_by("fueling_date")
    )

    advances = list(
        Advance.objects.filter(
            tenant=tenant,
            driver=driver,
            is_active=True,
            status=Advance.Status.PAID,
            payment_date__gte=period_start,
            payment_date__lte=period_end,
        ).order_by("payment_date")
    )

    # ── Cálculos ──────────────────────────────────────────────────
    total_gross_kg = sum(w.gross_weight for w in waybills)
    total_tare_kg = sum(w.tare_weight for w in waybills)
    total_net_kg = total_gross_kg - total_tare_kg

    total_production_value = sum(
        (w.net_weight_tons * w.unit_price).quantize(Decimal("0.01")) for w in waybills
    )
    total_fueling_value = sum(
        f.driver_debit_total for f in fuelings
    )
    total_advance_value = sum(a.amount for a in advances)
    total_debits = total_fueling_value + total_advance_value
    net_balance = total_production_value - total_debits

    # Dados do proprietário para o snapshot (congela no momento do fechamento)
    proprietario_data = {}
    if proprietario:
        proprietario_data = {
            "name": proprietario.name,
            "document": proprietario.document,
            "phone": proprietario.phone,
            "bank_name": proprietario.bank_name,
            "bank_agency": proprietario.bank_agency,
            "bank_account": proprietario.bank_account,
            "bank_account_type": proprietario.get_bank_account_type_display(),
            "pix_key": proprietario.pix_key,
            "pix_key_type": proprietario.get_pix_key_type_display() if proprietario.pix_key else "",
        }

    vehicle_data = {}
    if vehicle:
        vehicle_data = {"plate": vehicle.plate, "brand": vehicle.brand, "model": vehicle.model}

    snapshot_data = {
        "driver": {
            "name": driver.name,
            "cpf": driver.document_cpf,
            "cnh": getattr(driver, "document_cnh", ""),
        },
        "proprietario": proprietario_data,
        "vehicle": vehicle_data,
        "period": {
            "start": period_start.isoformat(),
            "end": period_end.isoformat(),
        },
        "waybills": [
            {
                "number": w.number,
                "date": w.operation_date.isoformat(),
                "field": w.field.name if w.field else "",
                "vehicle": w.vehicle.plate,
                "gross_kg": float(w.gross_weight),
                "tare_kg": float(w.tare_weight),
                "net_kg": float(w.net_weight),
                "net_tons": float(w.net_weight_tons),
                "unit_price": float(w.unit_price),
                "total_value": float((w.net_weight_tons * w.unit_price).quantize(Decimal("0.01"))),
            }
            for w in waybills
        ],
        "fuelings": [
            {
                "date": f.fueling_date.isoformat(),
                "vehicle": f.vehicle.plate if f.vehicle_id else "",
                "fuel_type": f.get_fuel_type_display(),
                "liters": float(f.liters),
                "posted_price": float(f.posted_price_per_liter) if f.posted_price_per_liter else None,
                "driver_price": float(f.driver_price_per_liter),
                "extras_amount": float(f.extras_amount),
                "total": float(f.driver_debit_total),
            }
            for f in fuelings
        ],
        "advances": [
            {
                "date": a.payment_date.isoformat(),
                "amount": float(a.amount),
                "method": a.get_payment_method_display(),
                "reference": a.reference_code,
            }
            for a in advances
        ],
        "totals": {
            "net_kg": float(total_net_kg),
            "net_tons": float(total_net_kg / Decimal("1000")),
            "production_value": float(total_production_value),
            "fueling_debit": float(total_fueling_value),
            "advance_debit": float(total_advance_value),
            "total_debits": float(total_debits),
            "net_balance": float(net_balance),
            "waybill_count": len(waybills),
        },
    }

    settlement = Settlement.objects.create(
        tenant=tenant,
        account=settlement_account,
        settlement_type=Settlement.SettlementType.DRIVER,
        status=Settlement.Status.DRAFT,
        period_start=period_start,
        period_end=period_end,
        snapshot_total_production=total_net_kg,
        snapshot_total_credits=total_production_value,
        snapshot_total_debits=total_debits,
        snapshot_net_balance=net_balance,
        snapshot_waybill_count=len(waybills),
        snapshot_data=snapshot_data,
    )

    LedgerEntry.objects.filter(
        account=settlement_account,
        is_active=True,
        is_reversed=False,
        competence_date__gte=period_start,
        competence_date__lte=period_end,
    ).update(settlement=settlement)

    waybill_ids = [w.pk for w in waybills]
    Waybill.objects.filter(pk__in=waybill_ids).update(
        status=Waybill.Status.SETTLED,
        settlement=settlement,
    )

    return settlement


@transaction.atomic
def submit_settlement(settlement) -> None:
    """
    DRAFT → PENDING_APPROVAL.
    Envia o fechamento para revisão/aprovação.
    """
    from apps.finance.models import Settlement

    if settlement.status != Settlement.Status.DRAFT:
        raise ValueError(
            f"Só é possível enviar fechamentos em rascunho. "
            f"Status atual: {settlement.get_status_display()}"
        )
    settlement.status = Settlement.Status.PENDING_APPROVAL
    settlement.save(update_fields=["status", "updated_at"])


@transaction.atomic
def approve_settlement(settlement, approved_by=None) -> None:
    """
    PENDING_APPROVAL → APPROVED.
    Registra quem aprovou e quando.
    """
    from apps.finance.models import Settlement

    if settlement.status != Settlement.Status.PENDING_APPROVAL:
        raise ValueError(
            f"Só é possível aprovar fechamentos aguardando aprovação. "
            f"Status atual: {settlement.get_status_display()}"
        )
    settlement.status = Settlement.Status.APPROVED
    settlement.approved_by = approved_by
    settlement.approved_at = timezone.now()
    settlement.save(update_fields=["status", "approved_by", "approved_at", "updated_at"])


@transaction.atomic
def close_settlement(settlement, closed_by=None) -> None:
    """
    APPROVED → CLOSED.
    Congela definitivamente — registra closed_at.
    """
    from apps.finance.models import Settlement

    if settlement.status != Settlement.Status.APPROVED:
        raise ValueError(
            f"Só é possível fechar fechamentos aprovados. "
            f"Status atual: {settlement.get_status_display()}"
        )
    settlement.status = Settlement.Status.CLOSED
    settlement.closed_at = timezone.now()
    settlement.save(update_fields=["status", "closed_at", "updated_at"])


@transaction.atomic
def cancel_settlement(settlement, reason: str = "") -> None:
    """
    Cancela um fechamento em aberto e reverte status dos romaneios.
    Não é possível cancelar fechamentos CLOSED.
    """
    from apps.finance.models import LedgerEntry, Settlement
    from apps.operations.models import Waybill

    if settlement.status == Settlement.Status.CLOSED:
        raise ValueError("Não é possível cancelar um fechamento já encerrado.")

    Waybill.objects.filter(
        settlement=settlement,
        status=Waybill.Status.SETTLED,
    ).update(status=Waybill.Status.CONFIRMED, settlement=None)

    LedgerEntry.objects.filter(settlement=settlement).update(settlement=None)

    settlement.status = Settlement.Status.CANCELLED
    settlement.save(update_fields=["status", "updated_at"])
