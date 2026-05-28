"""
SafraLog — apps/finance/services/ledger_service.py

Serviço central do ledger financeiro.

Regras:
- Ledger é IMUTÁVEL — nunca UPDATE/DELETE em LedgerEntry.
- Estornos criam contra-entradas via LedgerEntry.create_reversal().
- Todo crédito/débito passa por aqui — nunca criar LedgerEntry diretamente.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.finance.models import FinancialAccount, LedgerEntry

# ─────────────────────────────────────────────────────────────
# ENTRADA GENÉRICA
# ─────────────────────────────────────────────────────────────


@transaction.atomic
def create_entry(
    *,
    tenant,
    account: FinancialAccount,
    entry_type: str,
    direction: str,
    amount: Decimal,
    description: str,
    competence_date: date | None = None,
    quantity: Decimal | None = None,
    unit_price: Decimal | None = None,
    source=None,
    reference_code: str = "",
) -> LedgerEntry:
    """
    Cria uma entrada no ledger.

    Parâmetros:
        tenant          — tenant do contexto
        account         — FinancialAccount destino
        entry_type      — LedgerEntry.EntryType
        direction       — LedgerEntry.Direction (CREDIT ou DEBIT)
        amount          — valor positivo em R$
        description     — texto descritivo (aparece no extrato)
        competence_date — data de competência (padrão: hoje)
        quantity        — quantidade em kg/ton quando aplicável
        unit_price      — preço unitário quando aplicável
        source          — objeto Django de origem (romaneio, abastecimento, etc.)
        reference_code  — código externo opcional (número do romaneio, etc.)
    """
    if amount < 0:
        raise ValueError(
            "LedgerEntry.amount deve ser positivo. Use direction para indicar débito/crédito."
        )

    if competence_date is None:
        competence_date = timezone.localdate()

    source_type = None
    source_id = None
    if source is not None:
        from django.contrib.contenttypes.models import ContentType

        source_type = ContentType.objects.get_for_model(source)
        source_id = source.pk

    return LedgerEntry.objects.create(
        tenant=tenant,
        account=account,
        entry_type=entry_type,
        direction=direction,
        amount=amount,
        description=description,
        competence_date=competence_date,
        quantity=quantity,
        unit_price=unit_price,
        source_type=source_type,
        source_id=source_id,
        reference_code=reference_code,
    )


# ─────────────────────────────────────────────────────────────
# ROMANEIO
# ─────────────────────────────────────────────────────────────


@transaction.atomic
def record_waybill_production(
    *,
    tenant,
    account: FinancialAccount,
    waybill,
) -> LedgerEntry:
    """
    Registra produção de romaneio como crédito na conta do motorista.
    Crédito = motorista tem a receber pelo frete.
    Chamado por WaybillConfirmView ao confirmar romaneio.
    """
    net_weight_kg = waybill.gross_weight - waybill.tare_weight
    net_weight_tons = net_weight_kg / Decimal("1000")
    total_value = (net_weight_tons * waybill.unit_price).quantize(Decimal("0.01"))

    return create_entry(
        tenant=tenant,
        account=account,
        entry_type=LedgerEntry.EntryType.WAYBILL_PRODUCTION,
        direction=LedgerEntry.Direction.CREDIT,
        amount=total_value,
        description=(
            f"Romaneio #{waybill.number:05d} — "
            f"{net_weight_tons:.3f} t × R$ {waybill.unit_price:.4f}/t"
        ),
        competence_date=waybill.operation_date,
        quantity=net_weight_kg,
        unit_price=waybill.unit_price,
        source=waybill,
        reference_code=str(waybill.number),
    )


# ─────────────────────────────────────────────────────────────
# ABASTECIMENTO
# ─────────────────────────────────────────────────────────────


@transaction.atomic
def record_fueling_debit(
    *,
    tenant,
    account: FinancialAccount,
    fueling,
) -> LedgerEntry:
    """
    Registra abastecimento como débito na conta do motorista.
    Chamado por FuelingCreateView ao salvar abastecimento.
    """
    total_value = fueling.driver_debit_total

    extras_str = f" + R$ {fueling.extras_amount:.2f} extras" if fueling.extras_amount else ""
    return create_entry(
        tenant=tenant,
        account=account,
        entry_type=LedgerEntry.EntryType.FUELING_DEBIT,
        direction=LedgerEntry.Direction.DEBIT,
        amount=total_value,
        description=(
            f"Abastecimento — {fueling.liters:.2f} L × "
            f"R$ {fueling.driver_price_per_liter:.4f}/L{extras_str} | "
            f"{fueling.vehicle.plate}"
        ),
        competence_date=fueling.fueling_date,
        quantity=fueling.liters,
        unit_price=fueling.driver_price_per_liter,
        source=fueling,
    )


# ─────────────────────────────────────────────────────────────
# ADIANTAMENTO
# ─────────────────────────────────────────────────────────────


@transaction.atomic
def record_advance_debit(
    *,
    tenant,
    account: FinancialAccount,
    advance,
) -> LedgerEntry:
    """
    Registra adiantamento como débito na conta do motorista.
    Chamado por Advance.confirm() ao confirmar o pagamento.
    """
    return create_entry(
        tenant=tenant,
        account=account,
        entry_type=LedgerEntry.EntryType.ADVANCE_DEBIT,
        direction=LedgerEntry.Direction.DEBIT,
        amount=advance.amount,
        description=(
            f"Adiantamento — "
            f"{advance.get_payment_method_display()} | "
            f"{advance.notes or 'sem observação'}"
        ),
        competence_date=advance.payment_date,  # ← campo correto
        source=advance,
        reference_code=advance.reference_code or "",
    )


# ─────────────────────────────────────────────────────────────
# AJUSTE MANUAL
# ─────────────────────────────────────────────────────────────


@transaction.atomic
def record_adjustment(
    *,
    tenant,
    account: FinancialAccount,
    amount: Decimal,
    direction: str,
    description: str,
    competence_date: date | None = None,
    reference_code: str = "",
) -> LedgerEntry:
    """
    Registra ajuste manual (crédito ou débito) na conta.
    Uso: correções, bônus, descontos avulsos.
    """
    entry_type = (
        LedgerEntry.EntryType.ADJUSTMENT_CREDIT
        if direction == LedgerEntry.Direction.CREDIT
        else LedgerEntry.EntryType.ADJUSTMENT_DEBIT
    )
    return create_entry(
        tenant=tenant,
        account=account,
        entry_type=entry_type,
        direction=direction,
        amount=amount,
        description=description,
        competence_date=competence_date,
        reference_code=reference_code,
    )


# ─────────────────────────────────────────────────────────────
# SALDO
# ─────────────────────────────────────────────────────────────


def get_balance(account: FinancialAccount, until_date: date | None = None) -> Decimal:
    """
    Retorna saldo atual da conta.
    Delega para FinancialAccount.get_balance() que já está implementado no model.
    """
    return account.get_balance(until_date=until_date)


def get_balances_bulk(accounts: list[FinancialAccount]) -> dict:
    """
    Retorna saldos de múltiplas contas em uma query só.
    Útil para listar motoristas com saldo sem N+1.
    Retorna dict {str(account.pk): Decimal}
    """
    from django.db.models import Sum

    if not accounts:
        return {}

    account_ids = [a.pk for a in accounts]
    entries = (
        LedgerEntry.objects.filter(
            account_id__in=account_ids,
            is_reversed=False,
            is_active=True,
        )
        .values("account_id", "direction")
        .annotate(total=Sum("amount"))
    )

    raw: dict[str, dict] = {}
    for row in entries:
        aid = str(row["account_id"])
        raw.setdefault(aid, {"credit": Decimal("0"), "debit": Decimal("0")})
        raw[aid][row["direction"]] = row["total"] or Decimal("0")

    return {
        str(a.pk): (
            raw.get(str(a.pk), {}).get("credit", Decimal("0"))
            - raw.get(str(a.pk), {}).get("debit", Decimal("0"))
        )
        for a in accounts
    }
