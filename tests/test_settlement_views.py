"""
SafraLog — tests/test_settlement_views.py
Testa apps/finance/views/settlement.py via RequestFactory.
"""

from __future__ import annotations

import uuid

import pytest
from django.http import Http404

from apps.finance.models import Settlement
from apps.finance.views.settlement import (
    SettlementApproveView,
    SettlementCancelView,
    SettlementCloseView,
    SettlementCreateView,
    SettlementDetailView,
    SettlementListView,
    SettlementSubmitView,
)

# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def draft_settlement(db, tenant, driver, confirmed_waybill):
    from django.utils import timezone

    from apps.finance.services.settlement_service import create_settlement

    today = timezone.localdate()
    return create_settlement(
        tenant=tenant,
        driver=driver,
        period_start=today.replace(day=1),
        period_end=today,
    )


@pytest.fixture
def pending_settlement(db, draft_settlement):
    from apps.finance.services.settlement_service import submit_settlement

    submit_settlement(settlement=draft_settlement)
    draft_settlement.refresh_from_db()
    return draft_settlement


@pytest.fixture
def approved_settlement(db, pending_settlement, admin_user):
    from apps.finance.services.settlement_service import approve_settlement

    approve_settlement(settlement=pending_settlement, approved_by=admin_user)
    pending_settlement.refresh_from_db()
    return pending_settlement


def _req(rf, method, user, tenant, data=None):
    fn = getattr(rf, method)
    request = fn("/", data or {})
    request.user = user
    request.tenant = tenant
    return request


# ── SettlementListView ────────────────────────────────────────────────────────


class TestSettlementListView:
    def test_status_200_vazio(self, rf, admin_user, tenant):
        request = _req(rf, "get", admin_user, tenant)
        assert SettlementListView.as_view()(request).status_code == 200

    def test_status_200_com_dados(self, rf, admin_user, draft_settlement):
        request = _req(rf, "get", admin_user, draft_settlement.tenant)
        assert SettlementListView.as_view()(request).status_code == 200


# ── SettlementDetailView ──────────────────────────────────────────────────────


class TestSettlementDetailView:
    def test_draft_200(self, rf, admin_user, draft_settlement):
        request = _req(rf, "get", admin_user, draft_settlement.tenant)
        r = SettlementDetailView.as_view()(request, pk=draft_settlement.pk)
        assert r.status_code == 200

    def test_pending_200(self, rf, admin_user, pending_settlement):
        request = _req(rf, "get", admin_user, pending_settlement.tenant)
        r = SettlementDetailView.as_view()(request, pk=pending_settlement.pk)
        assert r.status_code == 200

    def test_approved_200(self, rf, admin_user, approved_settlement):
        request = _req(rf, "get", admin_user, approved_settlement.tenant)
        r = SettlementDetailView.as_view()(request, pk=approved_settlement.pk)
        assert r.status_code == 200


# ── SettlementCreateView ──────────────────────────────────────────────────────


class TestSettlementCreateView:
    def test_get_200(self, rf, admin_user, tenant):
        request = _req(rf, "get", admin_user, tenant)
        assert SettlementCreateView.as_view()(request).status_code == 200

    def test_post_driver_inexistente_redireciona(self, rf, admin_user, tenant):
        request = _req(
            rf,
            "post",
            admin_user,
            tenant,
            {
                "driver": str(uuid.uuid4()),
                "period_start": "invalido",
                "period_end": "invalido",
            },
        )
        assert SettlementCreateView.as_view()(request).status_code == 302

    def test_post_datas_invertidas_redireciona(self, rf, admin_user, tenant, driver):
        request = _req(
            rf,
            "post",
            admin_user,
            tenant,
            {
                "driver": str(driver.pk),
                "period_start": "2025-01-31",
                "period_end": "2025-01-01",
            },
        )
        assert SettlementCreateView.as_view()(request).status_code == 302

    def test_post_sem_romaneios_redireciona(self, rf, admin_user, tenant, driver):
        request = _req(
            rf,
            "post",
            admin_user,
            tenant,
            {
                "driver": str(driver.pk),
                "period_start": "2020-01-01",
                "period_end": "2020-01-31",
            },
        )
        assert SettlementCreateView.as_view()(request).status_code == 302

    def test_post_sucesso_cria_e_redireciona(self, rf, admin_user, confirmed_waybill):
        from django.utils import timezone

        today = timezone.localdate()
        driver = confirmed_waybill.driver
        tenant = confirmed_waybill.tenant
        request = _req(
            rf,
            "post",
            admin_user,
            tenant,
            {
                "driver": str(driver.pk),
                "period_start": today.replace(day=1).isoformat(),
                "period_end": today.isoformat(),
            },
        )
        assert SettlementCreateView.as_view()(request).status_code == 302
        assert Settlement.objects.filter(tenant=tenant).exists()


# ── SettlementSubmitView ──────────────────────────────────────────────────────


class TestSettlementSubmitView:
    def test_submit_draft_para_pending(self, rf, admin_user, draft_settlement):
        request = _req(rf, "post", admin_user, draft_settlement.tenant)
        r = SettlementSubmitView.as_view()(request, pk=draft_settlement.pk)
        assert r.status_code == 302
        draft_settlement.refresh_from_db()
        assert draft_settlement.status == Settlement.Status.PENDING_APPROVAL

    def test_submit_nao_draft_levanta_404(self, rf, admin_user, pending_settlement):
        request = _req(rf, "post", admin_user, pending_settlement.tenant)
        with pytest.raises(Http404):
            SettlementSubmitView.as_view()(request, pk=pending_settlement.pk)


# ── SettlementApproveView ─────────────────────────────────────────────────────


class TestSettlementApproveView:
    def test_approve_pending_para_approved(self, rf, admin_user, pending_settlement):
        request = _req(rf, "post", admin_user, pending_settlement.tenant)
        r = SettlementApproveView.as_view()(request, pk=pending_settlement.pk)
        assert r.status_code == 302
        pending_settlement.refresh_from_db()
        assert pending_settlement.status == Settlement.Status.APPROVED
        assert pending_settlement.approved_by == admin_user
        assert pending_settlement.approved_at is not None

    def test_approve_nao_pending_levanta_404(self, rf, admin_user, draft_settlement):
        request = _req(rf, "post", admin_user, draft_settlement.tenant)
        with pytest.raises(Http404):
            SettlementApproveView.as_view()(request, pk=draft_settlement.pk)


# ── SettlementCloseView ───────────────────────────────────────────────────────


class TestSettlementCloseView:
    def test_close_approved_para_closed(self, rf, admin_user, approved_settlement):
        request = _req(rf, "post", admin_user, approved_settlement.tenant)
        r = SettlementCloseView.as_view()(request, pk=approved_settlement.pk)
        assert r.status_code == 302
        approved_settlement.refresh_from_db()
        assert approved_settlement.status == Settlement.Status.CLOSED
        assert approved_settlement.closed_at is not None

    def test_close_nao_approved_levanta_404(self, rf, admin_user, draft_settlement):
        request = _req(rf, "post", admin_user, draft_settlement.tenant)
        with pytest.raises(Http404):
            SettlementCloseView.as_view()(request, pk=draft_settlement.pk)


# ── SettlementCancelView ──────────────────────────────────────────────────────


class TestSettlementCancelView:
    def test_cancel_draft(self, rf, admin_user, draft_settlement):
        request = _req(rf, "post", admin_user, draft_settlement.tenant)
        r = SettlementCancelView.as_view()(request, pk=draft_settlement.pk)
        assert r.status_code == 302
        draft_settlement.refresh_from_db()
        assert draft_settlement.status == Settlement.Status.CANCELLED

    def test_cancel_pending(self, rf, admin_user, pending_settlement):
        request = _req(rf, "post", admin_user, pending_settlement.tenant)
        r = SettlementCancelView.as_view()(request, pk=pending_settlement.pk)
        assert r.status_code == 302
        pending_settlement.refresh_from_db()
        assert pending_settlement.status == Settlement.Status.CANCELLED

    def test_cancel_approved(self, rf, admin_user, approved_settlement):
        request = _req(rf, "post", admin_user, approved_settlement.tenant)
        r = SettlementCancelView.as_view()(request, pk=approved_settlement.pk)
        assert r.status_code == 302
        approved_settlement.refresh_from_db()
        assert approved_settlement.status == Settlement.Status.CANCELLED

    def test_cancel_closed_nao_cancela(self, rf, admin_user, approved_settlement):
        from apps.finance.services.settlement_service import close_settlement

        close_settlement(settlement=approved_settlement, closed_by=admin_user)
        approved_settlement.refresh_from_db()

        request = _req(rf, "post", admin_user, approved_settlement.tenant)
        r = SettlementCancelView.as_view()(request, pk=approved_settlement.pk)
        assert r.status_code == 302
        approved_settlement.refresh_from_db()
        assert approved_settlement.status == Settlement.Status.CLOSED
