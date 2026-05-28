"""
Testes do ledger_service.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from apps.finance.models import LedgerEntry
from apps.finance.services import ledger_service
from tests.factories import DriverFactory


@pytest.mark.django_db
class TestCreateEntry:
    def test_cria_entrada_credito(self, tenant, driver):
        account = driver.financial_account
        entry = ledger_service.create_entry(
            tenant=tenant,
            account=account,
            entry_type=LedgerEntry.EntryType.WAYBILL_PRODUCTION,
            direction=LedgerEntry.Direction.CREDIT,
            amount=Decimal("1200.00"),
            description="Teste crédito",
        )
        assert entry.pk is not None
        assert entry.direction == LedgerEntry.Direction.CREDIT
        assert entry.amount == Decimal("1200.00")
        assert entry.is_reversed is False

    def test_rejeita_amount_negativo(self, tenant, driver):
        with pytest.raises(ValueError, match="positivo"):
            ledger_service.create_entry(
                tenant=tenant,
                account=driver.financial_account,
                entry_type="adjustment_credit",
                direction="credit",
                amount=Decimal("-100"),
                description="Inválido",
            )


@pytest.mark.django_db
class TestGetBalance:
    def test_saldo_zero_sem_lancamentos(self, driver):
        balance = ledger_service.get_balance(driver.financial_account)
        assert balance == Decimal("0")

    def test_saldo_com_credito_e_debito(self, tenant, driver):
        account = driver.financial_account
        ledger_service.create_entry(
            tenant=tenant,
            account=account,
            entry_type="waybill_production",
            direction="credit",
            amount=Decimal("1000.00"),
            description="Crédito",
        )
        ledger_service.create_entry(
            tenant=tenant,
            account=account,
            entry_type="fueling_debit",
            direction="debit",
            amount=Decimal("300.00"),
            description="Débito",
        )
        assert ledger_service.get_balance(account) == Decimal("700.00")


@pytest.mark.django_db
class TestRecordWaybillProduction:
    def test_cria_credito_ao_confirmar_romaneio(self, tenant, waybill, driver):
        account = driver.financial_account
        waybill.status = "confirmed"
        waybill.save()

        entry = ledger_service.record_waybill_production(
            tenant=tenant,
            account=account,
            waybill=waybill,
        )

        expected_net_kg = waybill.gross_weight - waybill.tare_weight
        expected_tons = expected_net_kg / Decimal("1000")
        expected_value = (expected_tons * waybill.unit_price).quantize(Decimal("0.01"))

        assert entry.direction == LedgerEntry.Direction.CREDIT
        assert entry.amount == expected_value
        assert entry.quantity == expected_net_kg


@pytest.mark.django_db
class TestGetBalancesBulk:
    def test_retorna_dict_com_pks(self, tenant):
        d1 = DriverFactory(tenant=tenant)
        d2 = DriverFactory(tenant=tenant)
        accounts = [d1.financial_account, d2.financial_account]

        balances = ledger_service.get_balances_bulk(accounts)

        assert str(d1.financial_account.pk) in balances
        assert str(d2.financial_account.pk) in balances

    def test_lista_vazia_retorna_dict_vazio(self):
        assert ledger_service.get_balances_bulk([]) == {}
