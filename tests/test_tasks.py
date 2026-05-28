"""
SafraLog — tests/test_tasks.py
Testa as tasks Celery de notificações:
  - check_cnh_expiry
  - check_negative_balances

Chamadas diretas via .apply() — sem broker real.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest

from apps.notifications.models import Notification
from apps.notifications.tasks import check_cnh_expiry, check_negative_balances

# ── Fixtures auxiliares ───────────────────────────────────────────────────────


@pytest.fixture
def driver_cnh_vencendo(db, driver, tenant):
    """Driver com CNH vencendo em 15 dias."""
    driver.cnh_expiry = date.today() + timedelta(days=15)
    driver.status = "active"
    driver.save(update_fields=["cnh_expiry", "status"])
    return driver


@pytest.fixture
def driver_cnh_ok(db, driver, tenant):
    """Driver com CNH longe de vencer (90 dias)."""
    driver.cnh_expiry = date.today() + timedelta(days=90)
    driver.status = "active"
    driver.save(update_fields=["cnh_expiry", "status"])
    return driver


@pytest.fixture
def driver_cnh_nula(db, driver):
    """Driver sem cnh_expiry definido."""
    driver.cnh_expiry = None
    driver.status = "active"
    driver.save(update_fields=["cnh_expiry", "status"])
    return driver


# ── check_cnh_expiry ──────────────────────────────────────────────────────────


class TestCheckCnhExpiry:
    def test_cria_notificacao_para_cnh_vencendo(self, db, driver_cnh_vencendo, admin_user):
        result = check_cnh_expiry.apply()

        assert result.result["created"] >= 1
        assert Notification.objects.filter(
            user=admin_user,
            level=Notification.Level.WARNING,
        ).exists()

    def test_notificacao_tem_titulo_correto(self, db, driver_cnh_vencendo, admin_user):
        check_cnh_expiry.apply()

        notif = Notification.objects.filter(
            user=admin_user,
            level=Notification.Level.WARNING,
        ).first()
        assert notif is not None
        assert driver_cnh_vencendo.name in notif.title
        assert "CNH vencendo" in notif.title

    def test_notificacao_tem_action_url(self, db, driver_cnh_vencendo, admin_user):
        check_cnh_expiry.apply()

        notif = Notification.objects.filter(user=admin_user).first()
        assert str(driver_cnh_vencendo.pk) in notif.action_url

    def test_nao_cria_para_cnh_ok(self, db, driver_cnh_ok, admin_user):
        result = check_cnh_expiry.apply()
        assert result.result["created"] == 0

    def test_nao_cria_para_cnh_nula(self, db, driver_cnh_nula, admin_user):
        """Driver com cnh_expiry=None não deve gerar notificação."""
        result = check_cnh_expiry.apply()
        assert result.result["created"] == 0

    def test_evita_duplicata_no_mesmo_dia(self, db, driver_cnh_vencendo, admin_user):
        """Segunda execução no mesmo dia não deve criar duplicata."""
        check_cnh_expiry.apply()
        count_antes = Notification.objects.filter(user=admin_user).count()

        check_cnh_expiry.apply()
        count_depois = Notification.objects.filter(user=admin_user).count()

        assert count_depois == count_antes

    def test_nao_notifica_operator(self, db, driver_cnh_vencendo, operator_user):
        """Operator não deve receber notificação — apenas admin e manager."""
        check_cnh_expiry.apply()
        assert not Notification.objects.filter(user=operator_user).exists()

    def test_notifica_manager(self, db, driver_cnh_vencendo, manager_user):
        check_cnh_expiry.apply()
        assert Notification.objects.filter(user=manager_user).exists()

    def test_retorna_dict_com_created(self, db, tenant):
        result = check_cnh_expiry.apply()
        assert isinstance(result.result, dict)
        assert "created" in result.result

    def test_driver_inativo_ignorado(self, db, driver, admin_user):
        """Driver inativo não deve gerar notificação mesmo com CNH vencendo."""
        driver.cnh_expiry = date.today() + timedelta(days=5)
        driver.status = "inactive"
        driver.save(update_fields=["cnh_expiry", "status"])

        result = check_cnh_expiry.apply()
        assert result.result["created"] == 0


# ── check_negative_balances ───────────────────────────────────────────────────


class TestCheckNegativeBalances:
    def test_sem_saldo_negativo_nao_cria(self, db, tenant, driver, admin_user):
        """Driver sem débitos → saldo 0 ou positivo → sem notificação."""
        result = check_negative_balances.apply()
        assert result.result["created"] == 0

    def test_cria_notificacao_para_saldo_negativo(
        self, db, driver, admin_user, financial_account, tenant
    ):
        """Debita conta do driver e verifica se notificação é criada."""
        from apps.finance.models import LedgerEntry

        # Cria débito diretamente para forçar saldo negativo
        LedgerEntry.objects.create(
            tenant=tenant,
            account=financial_account,
            entry_type=LedgerEntry.EntryType.ADVANCE_DEBIT,
            direction=LedgerEntry.Direction.DEBIT,
            amount=Decimal("500.00"),
            description="Débito de teste",
            competence_date=date.today(),
        )

        result = check_negative_balances.apply()
        assert result.result["created"] >= 1
        assert Notification.objects.filter(
            user=admin_user,
            level=Notification.Level.ERROR,
        ).exists()

    def test_notificacao_saldo_negativo_tem_titulo(
        self, db, driver, admin_user, financial_account, tenant
    ):
        from apps.finance.models import LedgerEntry

        LedgerEntry.objects.create(
            tenant=tenant,
            account=financial_account,
            entry_type=LedgerEntry.EntryType.ADVANCE_DEBIT,
            direction=LedgerEntry.Direction.DEBIT,
            amount=Decimal("300.00"),
            description="Débito de teste",
            competence_date=date.today(),
        )

        check_negative_balances.apply()

        notif = Notification.objects.filter(
            user=admin_user,
            level=Notification.Level.ERROR,
        ).first()
        assert notif is not None
        assert "Saldo negativo" in notif.title
        assert "300" in notif.message

    def test_evita_duplicata_no_mesmo_dia(self, db, driver, admin_user, financial_account, tenant):
        from apps.finance.models import LedgerEntry

        LedgerEntry.objects.create(
            tenant=tenant,
            account=financial_account,
            entry_type=LedgerEntry.EntryType.ADVANCE_DEBIT,
            direction=LedgerEntry.Direction.DEBIT,
            amount=Decimal("100.00"),
            description="Débito",
            competence_date=date.today(),
        )

        check_negative_balances.apply()
        count_antes = Notification.objects.filter(user=admin_user).count()

        check_negative_balances.apply()
        count_depois = Notification.objects.filter(user=admin_user).count()

        assert count_depois == count_antes

    def test_nao_notifica_operator(self, db, driver, operator_user, financial_account, tenant):
        from apps.finance.models import LedgerEntry

        LedgerEntry.objects.create(
            tenant=tenant,
            account=financial_account,
            entry_type=LedgerEntry.EntryType.ADVANCE_DEBIT,
            direction=LedgerEntry.Direction.DEBIT,
            amount=Decimal("200.00"),
            description="Débito",
            competence_date=date.today(),
        )

        check_negative_balances.apply()
        assert not Notification.objects.filter(user=operator_user).exists()

    def test_action_url_aponta_para_acertos(
        self, db, driver, admin_user, financial_account, tenant
    ):
        from apps.finance.models import LedgerEntry

        LedgerEntry.objects.create(
            tenant=tenant,
            account=financial_account,
            entry_type=LedgerEntry.EntryType.ADVANCE_DEBIT,
            direction=LedgerEntry.Direction.DEBIT,
            amount=Decimal("150.00"),
            description="Débito",
            competence_date=date.today(),
        )

        check_negative_balances.apply()

        notif = Notification.objects.filter(
            user=admin_user,
            level=Notification.Level.ERROR,
        ).first()
        assert notif is not None
        assert "acertos" in notif.action_url

    def test_retorna_dict_com_created(self, db, tenant):
        result = check_negative_balances.apply()
        assert isinstance(result.result, dict)
        assert "created" in result.result

    def test_ignora_conta_nao_driver(self, db, tenant, admin_user):
        """Contas do tipo OPERATIONAL não devem gerar notificação."""
        from apps.finance.models import FinancialAccount, LedgerEntry

        acc = FinancialAccount.objects.create(
            tenant=tenant,
            name="Conta Operacional",
            account_type=FinancialAccount.AccountType.OPERATIONAL,
        )
        LedgerEntry.objects.create(
            tenant=tenant,
            account=acc,
            entry_type=LedgerEntry.EntryType.ADJUSTMENT_DEBIT,
            direction=LedgerEntry.Direction.DEBIT,
            amount=Decimal("999.00"),
            description="Débito operacional",
            competence_date=date.today(),
        )

        result = check_negative_balances.apply()
        assert result.result["created"] == 0
