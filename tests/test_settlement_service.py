"""
SafraLog — tests/test_settlement.py
Testa o fluxo completo de fechamento financeiro:
create → submit → approve → close → cancel
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from apps.finance.models import LedgerEntry, Settlement
from apps.finance.services.ledger_service import record_waybill_production
from apps.finance.services.settlement_service import (
    approve_settlement,
    cancel_settlement,
    close_settlement,
    create_settlement,
    submit_settlement,
)
from apps.operations.models import Waybill

# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def period():
    return date(2025, 1, 1), date(2025, 1, 31)


@pytest.fixture
def confirmed_waybill_for_settlement(db, tenant, harvest, field, driver, vehicle):
    """Romaneio CONFIRMED com LedgerEntry — pronto para ser fechado."""
    from tests.factories import WaybillFactory

    waybill = WaybillFactory(
        tenant=tenant,
        harvest=harvest,
        field=field,
        driver=driver,
        vehicle=vehicle,
        status=Waybill.Status.CONFIRMED,
        operation_date=date(2025, 1, 15),
    )
    entry = record_waybill_production(
        tenant=tenant,
        account=driver.financial_account,
        waybill=waybill,
    )
    Waybill.objects.filter(pk=waybill.pk).update(ledger_entry=entry)
    waybill.refresh_from_db()
    return waybill


@pytest.fixture
def draft_settlement(db, tenant, driver, confirmed_waybill_for_settlement, period):
    """Settlement em DRAFT criado via service."""
    period_start, period_end = period
    return create_settlement(
        tenant=tenant,
        driver=driver,
        period_start=period_start,
        period_end=period_end,
    )


# ── create_settlement ─────────────────────────────────────────────────────────


class TestCreateSettlement:
    def test_cria_em_draft(self, draft_settlement):
        assert draft_settlement.status == Settlement.Status.DRAFT

    def test_marca_romaneios_como_settled(self, draft_settlement, confirmed_waybill_for_settlement):
        confirmed_waybill_for_settlement.refresh_from_db()
        assert confirmed_waybill_for_settlement.status == Waybill.Status.SETTLED
        assert confirmed_waybill_for_settlement.settlement_id == draft_settlement.pk

    def test_snapshot_preenchido(self, draft_settlement):
        assert draft_settlement.snapshot_net_balance is not None
        assert draft_settlement.snapshot_waybill_count == 1
        assert draft_settlement.snapshot_data != {}
        assert "totals" in draft_settlement.snapshot_data
        assert "waybills" in draft_settlement.snapshot_data

    def test_ledger_entries_vinculadas(self, draft_settlement, driver):
        entries = LedgerEntry.objects.filter(
            account=driver.financial_account,
            settlement=draft_settlement,
        )
        assert entries.exists()

    def test_raises_sem_romaneios(self, db, tenant, driver, period):
        period_start, period_end = period
        with pytest.raises(ValueError, match="Nenhum romaneio confirmado"):
            create_settlement(
                tenant=tenant,
                driver=driver,
                period_start=period_start,
                period_end=period_end,
            )

    def test_raises_fechamento_duplicado(
        self, db, tenant, driver, draft_settlement, confirmed_waybill_for_settlement, period
    ):
        period_start, period_end = period
        with pytest.raises(ValueError, match="Já existe um fechamento"):
            create_settlement(
                tenant=tenant,
                driver=driver,
                period_start=period_start,
                period_end=period_end,
            )

    def test_calculo_net_balance_correto(self, draft_settlement, confirmed_waybill_for_settlement):
        waybill = confirmed_waybill_for_settlement
        expected = (waybill.net_weight_tons * waybill.unit_price).quantize(Decimal("0.01"))
        assert draft_settlement.snapshot_net_balance == expected
        assert draft_settlement.snapshot_total_credits == expected
        assert draft_settlement.snapshot_total_debits == Decimal("0")


# ── submit_settlement ─────────────────────────────────────────────────────────


class TestSubmitSettlement:
    def test_draft_para_pending_approval(self, draft_settlement):
        submit_settlement(settlement=draft_settlement)
        draft_settlement.refresh_from_db()
        assert draft_settlement.status == Settlement.Status.PENDING_APPROVAL

    def test_raises_se_nao_draft(self, draft_settlement):
        submit_settlement(settlement=draft_settlement)
        draft_settlement.refresh_from_db()
        with pytest.raises(ValueError, match="rascunho"):
            submit_settlement(settlement=draft_settlement)


# ── approve_settlement ────────────────────────────────────────────────────────


class TestApproveSettlement:
    def test_pending_para_approved(self, draft_settlement, admin_user):
        submit_settlement(settlement=draft_settlement)
        draft_settlement.refresh_from_db()
        approve_settlement(settlement=draft_settlement, approved_by=admin_user)
        draft_settlement.refresh_from_db()
        assert draft_settlement.status == Settlement.Status.APPROVED
        assert draft_settlement.approved_by == admin_user
        assert draft_settlement.approved_at is not None

    def test_raises_se_nao_pending(self, draft_settlement, admin_user):
        with pytest.raises(ValueError, match="aprovação"):
            approve_settlement(settlement=draft_settlement, approved_by=admin_user)


# ── close_settlement ──────────────────────────────────────────────────────────


class TestCloseSettlement:
    def test_approved_para_closed(self, draft_settlement, admin_user):
        submit_settlement(settlement=draft_settlement)
        draft_settlement.refresh_from_db()
        approve_settlement(settlement=draft_settlement, approved_by=admin_user)
        draft_settlement.refresh_from_db()
        close_settlement(settlement=draft_settlement, closed_by=admin_user)
        draft_settlement.refresh_from_db()
        assert draft_settlement.status == Settlement.Status.CLOSED
        assert draft_settlement.closed_at is not None

    def test_raises_se_nao_approved(self, draft_settlement):
        with pytest.raises(ValueError, match="aprovados"):
            close_settlement(settlement=draft_settlement)

    def test_snapshot_preservado_apos_close(self, draft_settlement, admin_user):
        submit_settlement(settlement=draft_settlement)
        draft_settlement.refresh_from_db()
        approve_settlement(settlement=draft_settlement, approved_by=admin_user)
        draft_settlement.refresh_from_db()
        net_antes = draft_settlement.snapshot_net_balance
        close_settlement(settlement=draft_settlement, closed_by=admin_user)
        draft_settlement.refresh_from_db()
        assert draft_settlement.snapshot_net_balance == net_antes

    def test_get_net_balance_usa_snapshot_apos_close(self, draft_settlement, admin_user):
        submit_settlement(settlement=draft_settlement)
        draft_settlement.refresh_from_db()
        approve_settlement(settlement=draft_settlement, approved_by=admin_user)
        draft_settlement.refresh_from_db()
        close_settlement(settlement=draft_settlement, closed_by=admin_user)
        draft_settlement.refresh_from_db()
        # Deve usar snapshot, não recalcular do ledger
        assert draft_settlement.get_net_balance() == draft_settlement.snapshot_net_balance


# ── Fluxo completo end-to-end ─────────────────────────────────────────────────


class TestSettlementFluxoCompleto:
    def test_create_submit_approve_close(self, draft_settlement, admin_user):
        """Fluxo completo sem desvios."""
        s = draft_settlement

        assert s.status == Settlement.Status.DRAFT

        submit_settlement(settlement=s)
        s.refresh_from_db()
        assert s.status == Settlement.Status.PENDING_APPROVAL

        approve_settlement(settlement=s, approved_by=admin_user)
        s.refresh_from_db()
        assert s.status == Settlement.Status.APPROVED
        assert s.approved_by_id is not None

        close_settlement(settlement=s, closed_by=admin_user)
        s.refresh_from_db()
        assert s.status == Settlement.Status.CLOSED
        assert s.closed_at is not None

    def test_nao_pode_fechar_sem_aprovacao(self, draft_settlement):
        with pytest.raises(ValueError):
            close_settlement(settlement=draft_settlement)

    def test_nao_pode_aprovar_sem_submit(self, draft_settlement, admin_user):
        with pytest.raises(ValueError):
            approve_settlement(settlement=draft_settlement, approved_by=admin_user)


# ── cancel_settlement ─────────────────────────────────────────────────────────


class TestCancelSettlement:
    def test_cancela_draft(self, draft_settlement, confirmed_waybill_for_settlement):
        cancel_settlement(settlement=draft_settlement)
        draft_settlement.refresh_from_db()
        assert draft_settlement.status == Settlement.Status.CANCELLED

        confirmed_waybill_for_settlement.refresh_from_db()
        assert confirmed_waybill_for_settlement.status == Waybill.Status.CONFIRMED
        assert confirmed_waybill_for_settlement.settlement_id is None

    def test_cancela_pending(self, draft_settlement, confirmed_waybill_for_settlement):
        submit_settlement(settlement=draft_settlement)
        draft_settlement.refresh_from_db()
        cancel_settlement(settlement=draft_settlement)
        draft_settlement.refresh_from_db()
        assert draft_settlement.status == Settlement.Status.CANCELLED

    def test_cancela_approved(self, draft_settlement, admin_user, confirmed_waybill_for_settlement):
        submit_settlement(settlement=draft_settlement)
        draft_settlement.refresh_from_db()
        approve_settlement(settlement=draft_settlement, approved_by=admin_user)
        draft_settlement.refresh_from_db()
        cancel_settlement(settlement=draft_settlement)
        draft_settlement.refresh_from_db()
        assert draft_settlement.status == Settlement.Status.CANCELLED

        confirmed_waybill_for_settlement.refresh_from_db()
        assert confirmed_waybill_for_settlement.status == Waybill.Status.CONFIRMED

    def test_raises_cancelar_closed(self, draft_settlement, admin_user):
        submit_settlement(settlement=draft_settlement)
        draft_settlement.refresh_from_db()
        approve_settlement(settlement=draft_settlement, approved_by=admin_user)
        draft_settlement.refresh_from_db()
        close_settlement(settlement=draft_settlement, closed_by=admin_user)
        draft_settlement.refresh_from_db()
        with pytest.raises(ValueError, match="encerrado"):
            cancel_settlement(settlement=draft_settlement)

    def test_ledger_entries_desvinculadas_apos_cancel(self, draft_settlement, driver):
        cancel_settlement(settlement=draft_settlement)
        entries_vinculadas = LedgerEntry.objects.filter(
            account=driver.financial_account,
            settlement=draft_settlement,
        )
        assert not entries_vinculadas.exists()
