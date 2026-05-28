"""
SafraLog — tests/test_advance.py
Testa Advance.confirm() e Advance.cancel() com integração ao ledger.
"""

from __future__ import annotations

import pytest

from apps.finance.models import Advance, LedgerEntry

# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def pending_advance(db, advance):
    """Adiantamento PENDING pronto para confirm()."""
    assert advance.status == Advance.Status.PENDING
    return advance


@pytest.fixture
def paid_advance(db, advance):
    """Adiantamento já confirmado (PAID) com LedgerEntry vinculada."""
    advance.confirm()
    advance.refresh_from_db()
    return advance


# ── confirm() ─────────────────────────────────────────────────────────────────


class TestAdvanceConfirm:
    def test_muda_status_para_paid(self, pending_advance):
        pending_advance.confirm()
        pending_advance.refresh_from_db()
        assert pending_advance.status == Advance.Status.PAID

    def test_cria_ledger_entry_debit(self, pending_advance):
        pending_advance.confirm()
        pending_advance.refresh_from_db()

        assert pending_advance.ledger_entry is not None
        entry = pending_advance.ledger_entry
        assert entry.direction == LedgerEntry.Direction.DEBIT
        assert entry.entry_type == LedgerEntry.EntryType.ADVANCE_DEBIT
        assert entry.amount == pending_advance.amount

    def test_ledger_entry_vinculada_a_conta(self, pending_advance):
        pending_advance.confirm()
        pending_advance.refresh_from_db()

        entry = pending_advance.ledger_entry
        assert entry.account == pending_advance.financial_account

    def test_debita_saldo_do_motorista(self, pending_advance):
        account = pending_advance.financial_account
        saldo_antes = account.get_balance()

        pending_advance.confirm()

        saldo_depois = account.get_balance()
        assert saldo_depois == saldo_antes - pending_advance.amount

    def test_raises_se_ja_pago(self, paid_advance):
        with pytest.raises(ValueError, match="pendentes"):
            paid_advance.confirm()

    def test_raises_se_cancelado(self, pending_advance):
        pending_advance.cancel()
        pending_advance.refresh_from_db()

        with pytest.raises(ValueError, match="pendentes"):
            pending_advance.confirm()

    def test_atomicidade_confirm(self, pending_advance, monkeypatch):
        """Se o save() falhar após criar a LedgerEntry, tudo deve ser revertido."""
        original_save = pending_advance.save

        call_count = 0

        def failing_save(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count > 0:
                raise RuntimeError("DB failure simulada")
            return original_save(*args, **kwargs)

        monkeypatch.setattr(pending_advance, "save", failing_save)

        with pytest.raises(RuntimeError):
            pending_advance.confirm()

        # Rollback — status deve continuar PENDING
        pending_advance.refresh_from_db()
        assert pending_advance.status == Advance.Status.PENDING
        assert pending_advance.ledger_entry_id is None

        # LedgerEntry não deve ter sido criada
        assert not LedgerEntry.objects.filter(
            entry_type=LedgerEntry.EntryType.ADVANCE_DEBIT,
            account=pending_advance.financial_account,
        ).exists()


# ── cancel() ──────────────────────────────────────────────────────────────────


class TestAdvanceCancel:
    def test_cancela_pending(self, pending_advance):
        pending_advance.cancel()
        pending_advance.refresh_from_db()
        assert pending_advance.status == Advance.Status.CANCELLED

    def test_cancela_pending_sem_ledger_entry(self, pending_advance):
        """PENDING não tem ledger — cancela sem criar reversal."""
        pending_advance.cancel()

        assert not LedgerEntry.objects.filter(
            entry_type=LedgerEntry.EntryType.REVERSAL,
            account=pending_advance.financial_account,
        ).exists()

    def test_cancela_paid_cria_reversal(self, paid_advance):
        """PAID tem ledger — cancela e cria REVERSAL."""
        entry = paid_advance.ledger_entry
        paid_advance.cancel(reason="Erro no pagamento")
        paid_advance.refresh_from_db()

        assert paid_advance.status == Advance.Status.CANCELLED

        entry.refresh_from_db()
        assert entry.is_reversed is True

        reversal = LedgerEntry.objects.get(pk=entry.reversal_entry_id)
        assert reversal.direction == LedgerEntry.Direction.CREDIT
        assert reversal.amount == entry.amount
        assert "Erro no pagamento" in reversal.description

    def test_cancela_paid_restaura_saldo(self, paid_advance):
        """Após cancelar adiantamento pago, saldo do motorista volta ao original."""
        account = paid_advance.financial_account
        # Saldo após confirm() = -amount (débito)
        saldo_apos_confirm = account.get_balance()

        paid_advance.cancel()

        saldo_apos_cancel = account.get_balance()
        # Reversal (crédito) cancela o débito — saldo volta
        assert saldo_apos_cancel == saldo_apos_confirm + paid_advance.amount

    def test_raises_se_ja_cancelado(self, pending_advance):
        pending_advance.cancel()
        pending_advance.refresh_from_db()

        with pytest.raises(ValueError, match="já cancelado"):
            pending_advance.cancel()

    def test_cancel_sem_reason_usa_padrao(self, paid_advance):
        entry = paid_advance.ledger_entry
        paid_advance.cancel()  # sem reason

        entry.refresh_from_db()
        reversal = LedgerEntry.objects.get(pk=entry.reversal_entry_id)
        assert "Cancelamento de adiantamento" in reversal.description

    def test_atomicidade_cancel_paid(self, paid_advance, monkeypatch):
        """Se save() falhar após reversal, rollback total."""
        original_save = paid_advance.save

        call_count = 0

        def failing_save(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count > 0:
                raise RuntimeError("DB failure")
            return original_save(*args, **kwargs)

        monkeypatch.setattr(paid_advance, "save", failing_save)

        with pytest.raises(RuntimeError):
            paid_advance.cancel()

        # Rollback — status deve continuar PAID
        paid_advance.refresh_from_db()
        assert paid_advance.status == Advance.Status.PAID

        # LedgerEntry não deve estar marcada como revertida
        entry = paid_advance.ledger_entry
        entry.refresh_from_db()
        assert entry.is_reversed is False
