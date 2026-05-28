"""
SafraLog — tests/conftest.py
Fixtures compartilhadas entre todos os testes.
"""

from __future__ import annotations

import pytest
from django.test import RequestFactory

from tests.factories import (
    AdvanceFactory,
    DriverFactory,
    FieldFactory,
    FuelingFactory,
    HarvestFactory,
    LedgerEntryFactory,
    TenantFactory,
    UserFactory,
    VehicleFactory,
    WaybillFactory,
)

# ── Infraestrutura ────────────────────────────────────────────────────────────


@pytest.fixture
def rf():
    """
    RequestFactory com suporte a messages.
    """
    from django.contrib.messages.storage.fallback import FallbackStorage

    factory = RequestFactory()
    original_post = factory.post
    original_get = factory.get

    def _patch(request):
        request.session = {}
        request._messages = FallbackStorage(request)
        return request

    factory.post = lambda *a, **kw: _patch(original_post(*a, **kw))
    factory.get = lambda *a, **kw: _patch(original_get(*a, **kw))
    return factory


# ── Tenant ────────────────────────────────────────────────────────────────────


@pytest.fixture
def tenant(db):
    return TenantFactory()


# ── Usuários ──────────────────────────────────────────────────────────────────


@pytest.fixture
def admin_user(db, tenant):
    return UserFactory(tenant=tenant, role="admin")


@pytest.fixture
def manager_user(db, tenant):
    return UserFactory(tenant=tenant, role="manager")


@pytest.fixture
def operator_user(db, tenant):
    return UserFactory(tenant=tenant, role="operator")


# ── Clients autenticados ──────────────────────────────────────────────────────


@pytest.fixture
def client_admin(db, admin_user):
    return _make_client(admin_user)


@pytest.fixture
def client_manager(db, manager_user):
    return _make_client(manager_user)


@pytest.fixture
def client_operator(db, operator_user):
    return _make_client(operator_user)


# ── Operações ─────────────────────────────────────────────────────────────────


@pytest.fixture
def harvest(db, tenant):
    return HarvestFactory(tenant=tenant)


@pytest.fixture
def field(db, tenant, harvest):
    return FieldFactory(tenant=tenant, harvest=harvest)


# ── Logística ─────────────────────────────────────────────────────────────────


@pytest.fixture
def driver(db, tenant):
    """Driver com financial_account criada automaticamente pelo post_generation."""
    return DriverFactory(tenant=tenant)


@pytest.fixture
def vehicle(db, tenant):
    return VehicleFactory(tenant=tenant)


@pytest.fixture
def fueling(db, driver, vehicle):
    return FuelingFactory(driver=driver, vehicle=vehicle)


# ── Financeiro ────────────────────────────────────────────────────────────────


@pytest.fixture
def financial_account(db, driver):
    """
    Retorna a conta financeira do driver.
    DriverFactory já cria a conta via post_generation — nunca duplicar.
    """
    return driver.financial_account


@pytest.fixture
def ledger_entry(db, financial_account, tenant):
    return LedgerEntryFactory(account=financial_account, tenant=tenant)


@pytest.fixture
def advance(db, driver):
    return AdvanceFactory(driver=driver)


# ── Romaneios ─────────────────────────────────────────────────────────────────


@pytest.fixture
def waybill(db, tenant, harvest, field, driver, vehicle):
    return WaybillFactory(
        tenant=tenant,
        harvest=harvest,
        field=field,
        driver=driver,
        vehicle=vehicle,
    )


@pytest.fixture
def waybill_factory(db, tenant, harvest, field, driver, vehicle):
    """
    Factory callable — permite criar múltiplos waybills com kwargs customizáveis.

    Uso:
        def test_algo(waybill_factory):
            draft     = waybill_factory(status="draft")
            confirmed = waybill_factory(status="confirmed")
    """

    def _factory(**kwargs):
        return WaybillFactory(
            tenant=tenant,
            harvest=harvest,
            field=field,
            driver=driver,
            vehicle=vehicle,
            **kwargs,
        )

    return _factory


@pytest.fixture
def confirmed_waybill(db, waybill_factory, financial_account, tenant):
    """
    Romaneio CONFIRMED com LedgerEntry de produção vinculada.
    Simula o fluxo real: WaybillConfirmView → record_waybill_production.
    """
    from apps.finance.services.ledger_service import record_waybill_production
    from apps.operations.models import Waybill

    waybill = waybill_factory(status=Waybill.Status.CONFIRMED)
    entry = record_waybill_production(
        tenant=tenant,
        account=financial_account,
        waybill=waybill,
    )
    Waybill.objects.filter(pk=waybill.pk).update(ledger_entry=entry)
    waybill.refresh_from_db()
    return waybill
