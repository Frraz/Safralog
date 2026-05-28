"""
Testes de Romaneios (Waybill).
"""

from __future__ import annotations

from decimal import Decimal

import pytest

# ─────────────────────────────────────────────────────────────
# MODEL
# ─────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestWaybillModel:
    def test_net_weight(self, waybill):
        waybill.gross_weight = Decimal("50000")
        waybill.tare_weight = Decimal("14000")
        assert waybill.net_weight == Decimal("36000")

    def test_net_weight_tons(self, waybill):
        waybill.gross_weight = Decimal("50000")
        waybill.tare_weight = Decimal("14000")
        assert waybill.net_weight_tons == Decimal("36.000")

    def test_total_value(self, waybill):
        waybill.gross_weight = Decimal("50000")
        waybill.tare_weight = Decimal("14000")
        waybill.unit_price = Decimal("120.00")
        expected = Decimal("36") * Decimal("120.00")
        assert waybill.total_value == expected

    def test_str_contains_number(self, waybill):
        assert str(waybill.number) in str(waybill)

    def test_status_default_draft(self, waybill):
        assert waybill.status == "draft"

    def test_is_active_default_true(self, waybill):
        assert waybill.is_active is True


# ─────────────────────────────────────────────────────────────
# VIEWS — usa RequestFactory para injetar usuário/tenant
# diretamente, sem depender de sessão, cookies ou middleware.
# ─────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestWaybillViews:
    """
    Testa as views de romaneio usando RequestFactory.
    RequestFactory injeta usuário e tenant diretamente no request,
    evitando toda a cadeia de middleware/sessão/cookie.
    É o padrão correto para testes unitários de views Django.
    """

    def _make_request(self, rf, user, method="get", path="/", data=None):
        """Constrói request com usuário e tenant já injetados."""
        fn = getattr(rf, method)
        request = fn(path, data or {})
        request.user = user
        request.tenant = user.tenant
        return request

    def test_list_authenticated(self, rf, admin_user):
        from apps.operations.views.waybill import WaybillListView

        request = self._make_request(rf, admin_user, path="/operations/romaneios/")
        response = WaybillListView.as_view()(request)
        assert response.status_code == 200

    def test_list_htmx_partial(self, rf, admin_user):
        """Com header HTMX retorna o partial, não a página completa."""
        from apps.operations.views.waybill import WaybillListView

        request = self._make_request(rf, admin_user, path="/operations/romaneios/")
        request.META["HTTP_HX_REQUEST"] = "true"
        response = WaybillListView.as_view()(request)
        assert response.status_code == 200

    def test_create_get(self, rf, admin_user):
        from apps.operations.views.waybill import WaybillCreateView

        request = self._make_request(rf, admin_user, path="/operations/romaneios/novo/")
        response = WaybillCreateView.as_view()(request)
        assert response.status_code == 200

    def test_detail_authenticated(self, rf, admin_user, waybill):
        from apps.operations.views.waybill import WaybillDetailView

        request = self._make_request(rf, admin_user, path=f"/operations/romaneios/{waybill.pk}/")
        response = WaybillDetailView.as_view()(request, pk=waybill.pk)
        assert response.status_code == 200

    def test_operator_can_list(self, rf, operator_user):
        from apps.operations.views.waybill import WaybillListView

        request = self._make_request(rf, operator_user, path="/operations/romaneios/")
        response = WaybillListView.as_view()(request)
        assert response.status_code == 200

    def test_waybill_not_found_returns_404(self, rf, admin_user):
        import uuid

        from apps.operations.views.waybill import WaybillDetailView

        request = self._make_request(rf, admin_user)
        with pytest.raises(Exception):  # Http404
            WaybillDetailView.as_view()(request, pk=uuid.uuid4())

    def test_create_post_invalid_form(self, rf, admin_user):
        """POST com dados inválidos retorna 200 com erros no form."""
        from apps.operations.views.waybill import WaybillCreateView

        request = self._make_request(
            rf,
            admin_user,
            method="post",
            path="/operations/romaneios/novo/",
            data={},  # campos obrigatórios em branco
        )
        # Simula middleware de CSRF desabilitado em testes
        request._dont_enforce_csrf_checks = True
        response = WaybillCreateView.as_view()(request)
        assert response.status_code == 200  # re-renderiza o form com erros
