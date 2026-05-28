"""
SafraLog — tests/test_waybill_cancel.py
Testa o fluxo de cancelamento de romaneio e reversal do ledger.
"""

import pytest

from apps.finance.models import LedgerEntry
from apps.finance.services.ledger_service import record_waybill_production
from apps.operations.models import Waybill

# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def confirmed_waybill(waybill_factory, financial_account):
    """Romaneio já confirmado com LedgerEntry vinculada."""
    waybill = waybill_factory(status=Waybill.Status.CONFIRMED)
    entry = record_waybill_production(
        tenant=waybill.tenant,
        account=financial_account,
        waybill=waybill,
    )
    Waybill.objects.filter(pk=waybill.pk).update(ledger_entry=entry)
    waybill.refresh_from_db()
    return waybill


# ── create_reversal ───────────────────────────────────────────────────────────


class TestCreateReversal:
    def test_cria_entrada_oposta(self, confirmed_waybill):
        entry = confirmed_waybill.ledger_entry
        reversal = entry.create_reversal()

        assert reversal.direction == LedgerEntry.Direction.DEBIT
        assert reversal.amount == entry.amount
        assert reversal.entry_type == LedgerEntry.EntryType.REVERSAL

    def test_marca_original_como_revertida(self, confirmed_waybill):
        entry = confirmed_waybill.ledger_entry
        reversal = entry.create_reversal()

        entry.refresh_from_db()
        assert entry.is_reversed is True
        assert entry.reversal_entry_id == reversal.pk

    def test_reason_aparece_na_descricao(self, confirmed_waybill):
        entry = confirmed_waybill.ledger_entry
        reversal = entry.create_reversal(reason="Erro de pesagem")

        assert "Erro de pesagem" in reversal.description

    def test_raises_se_ja_estornada(self, confirmed_waybill):
        entry = confirmed_waybill.ledger_entry
        entry.create_reversal()

        with pytest.raises(ValueError, match="já foi estornada"):
            entry.create_reversal()

    def test_atomicidade_reversal(self, confirmed_waybill, monkeypatch):
        """Se o save() final falhar, o reversal entry NÃO deve existir no banco."""
        entry = confirmed_waybill.ledger_entry
        original_save = entry.save

        call_count = 0

        def failing_save(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count > 0:
                raise RuntimeError("DB failure simulada")
            return original_save(*args, **kwargs)

        monkeypatch.setattr(entry, "save", failing_save)

        with pytest.raises(RuntimeError):
            entry.create_reversal()

        # O reversal entry NÃO deve ter sido persistido
        assert not LedgerEntry.objects.filter(
            entry_type=LedgerEntry.EntryType.REVERSAL,
            account=entry.account,
        ).exists()

        # A entrada original NÃO deve estar marcada como revertida
        entry.refresh_from_db()
        assert entry.is_reversed is False


# ── WaybillCancelView ─────────────────────────────────────────────────────────


class TestWaybillCancelView:
    def test_cancela_rascunho_sem_ledger(self, rf, admin_user, waybill_factory):
        waybill = waybill_factory(status=Waybill.Status.DRAFT)

        request = rf.post(f"/operations/romaneios/{waybill.pk}/cancelar/")
        request.user = admin_user
        request.tenant = waybill.tenant

        from apps.operations.views.waybill import WaybillCancelView

        WaybillCancelView.as_view()(request, pk=waybill.pk)

        waybill.refresh_from_db()  # ← faltava isso
        assert waybill.status == Waybill.Status.CANCELLED
        assert LedgerEntry.objects.filter(entry_type=LedgerEntry.EntryType.REVERSAL).count() == 0

    def test_cancela_confirmado_cria_reversal(self, rf, admin_user, confirmed_waybill):
        """Confirmado com LedgerEntry — deve criar REVERSAL e cancelar."""
        request = rf.post(
            f"/operations/romaneios/{confirmed_waybill.pk}/cancelar/",
            {"reason": "Pesagem incorreta"},
        )
        request.user = admin_user
        request.tenant = confirmed_waybill.tenant

        from apps.operations.views.waybill import WaybillCancelView

        response = WaybillCancelView.as_view()(request, pk=confirmed_waybill.pk)

        confirmed_waybill.refresh_from_db()
        assert confirmed_waybill.status == Waybill.Status.CANCELLED

        entry = confirmed_waybill.ledger_entry
        entry.refresh_from_db()
        assert entry.is_reversed is True

        reversal = LedgerEntry.objects.get(pk=entry.reversal_entry_id)
        assert reversal.direction == LedgerEntry.Direction.DEBIT
        assert reversal.amount == entry.amount
        assert "Pesagem incorreta" in reversal.description

    def test_saldo_zerado_apos_cancelamento(self, rf, admin_user, confirmed_waybill):
        """
        O reversal deve anular exatamente o crédito do romaneio.
        Saldo líquido das duas entradas (crédito + reversal débito) = 0.
        """
        from apps.finance.models import LedgerEntry

        account = confirmed_waybill.ledger_entry.account

        request = rf.post(f"/operations/romaneios/{confirmed_waybill.pk}/cancelar/")
        request.user = admin_user
        request.tenant = confirmed_waybill.tenant

        from apps.operations.views.waybill import WaybillCancelView

        WaybillCancelView.as_view()(request, pk=confirmed_waybill.pk)

        # Confirma que o reversal foi criado
        confirmed_waybill.ledger_entry.refresh_from_db()
        assert confirmed_waybill.ledger_entry.is_reversed is True

        # O saldo líquido das entradas desta conta deve ser 0
        # (crédito original anulado pelo débito de estorno)
        entries = LedgerEntry.objects.filter(account=account)
        total_credits = sum(e.amount for e in entries if e.direction == "credit")
        total_debits = sum(e.amount for e in entries if e.direction == "debit")
        assert total_credits == total_debits

    def test_nao_cancela_fechado(self, rf, admin_user, waybill_factory):
        """Romaneio SETTLED não pode ser cancelado diretamente."""
        waybill = waybill_factory(status=Waybill.Status.SETTLED)

        request = rf.post(f"/operations/romaneios/{waybill.pk}/cancelar/")
        request.user = admin_user
        request.tenant = waybill.tenant

        from apps.operations.views.waybill import WaybillCancelView

        WaybillCancelView.as_view()(request, pk=waybill.pk)

        waybill.refresh_from_db()
        assert waybill.status == Waybill.Status.SETTLED  # inalterado

    def test_atomicidade_cancelamento(self, rf, admin_user, confirmed_waybill, monkeypatch):
        """Se cancel() falhar após reversal, o ledger deve ser revertido (rollback)."""
        original_cancel = confirmed_waybill.cancel

        def failing_cancel(*args, **kwargs):
            raise RuntimeError("DB failure simulada no cancel")

        monkeypatch.setattr(confirmed_waybill.__class__, "cancel", failing_cancel)

        request = rf.post(f"/operations/romaneios/{confirmed_waybill.pk}/cancelar/")
        request.user = admin_user
        request.tenant = confirmed_waybill.tenant

        from apps.operations.views.waybill import WaybillCancelView

        # A view captura a exceção e exibe mensagem de erro — não estoura
        WaybillCancelView.as_view()(request, pk=confirmed_waybill.pk)

        # Romaneio NÃO deve ter sido cancelado
        confirmed_waybill.refresh_from_db()
        assert confirmed_waybill.status == Waybill.Status.CONFIRMED

        # LedgerEntry NÃO deve estar marcada como revertida (rollback)
        entry = confirmed_waybill.ledger_entry
        entry.refresh_from_db()
        assert entry.is_reversed is False


# ── WaybillConfirmView ────────────────────────────────────────────────────────


class TestWaybillConfirmView:
    def test_confirma_e_cria_ledger_entry(self, rf, admin_user, waybill_factory):
        waybill = waybill_factory(status=Waybill.Status.DRAFT)

        request = rf.post(f"/operations/romaneios/{waybill.pk}/confirmar/")
        request.user = admin_user
        request.tenant = waybill.tenant

        from apps.operations.views.waybill import WaybillConfirmView

        WaybillConfirmView.as_view()(request, pk=waybill.pk)

        waybill.refresh_from_db()
        assert waybill.status == Waybill.Status.CONFIRMED
        assert waybill.ledger_entry_id is not None

        entry = waybill.ledger_entry
        assert entry.direction == LedgerEntry.Direction.CREDIT
        assert entry.amount == waybill.total_value
        assert entry.entry_type == LedgerEntry.EntryType.WAYBILL_PRODUCTION

    def test_atomicidade_confirmacao(self, rf, admin_user, waybill_factory, monkeypatch):
        """Se record_waybill_production falhar, romaneio deve voltar a DRAFT."""
        waybill = waybill_factory(status=Waybill.Status.DRAFT)

        from apps.finance.services import ledger_service

        def failing_record(*args, **kwargs):
            raise RuntimeError("DB failure simulada no ledger")

        monkeypatch.setattr(ledger_service, "record_waybill_production", failing_record)

        request = rf.post(f"/operations/romaneios/{waybill.pk}/confirmar/")
        request.user = admin_user
        request.tenant = waybill.tenant

        from apps.operations.views.waybill import WaybillConfirmView

        WaybillConfirmView.as_view()(request, pk=waybill.pk)

        # Rollback — romaneio deve continuar DRAFT
        waybill.refresh_from_db()
        assert waybill.status == Waybill.Status.DRAFT
        assert waybill.ledger_entry_id is None
