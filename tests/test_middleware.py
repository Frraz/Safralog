"""
SafraLog — tests/test_middleware.py
Testa:
  - apps/core/middleware.py (TenantMiddleware, TimezoneMiddleware,
    LastSeenMiddleware, SecurityHeadersMiddleware)
  - apps/tenants/middleware.py (TenantMiddleware)
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from django.http import HttpResponse
from django.test import RequestFactory

from apps.core.middleware import (
    LastSeenMiddleware,
    SecurityHeadersMiddleware,
    TimezoneMiddleware,
)
from apps.core.middleware import TenantMiddleware as CoreTenantMiddleware
from apps.tenants.middleware import TenantMiddleware as TenantsTenantMiddleware

# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def rf():
    return RequestFactory()


def _anon_request(rf):
    request = rf.get("/")
    request.user = MagicMock()
    request.user.is_authenticated = False
    return request


def _auth_request(rf, user):
    request = rf.get("/")
    request.user = user
    return request


# ── CoreTenantMiddleware ──────────────────────────────────────────────────────


class TestCoreTenantMiddleware:
    def test_anonimo_seta_tenant_none(self, rf):
        mw = CoreTenantMiddleware(get_response=lambda r: HttpResponse())
        request = _anon_request(rf)
        mw.process_request(request)
        assert request.tenant is None

    def test_usuario_sem_tenant_id(self, rf):
        mw = CoreTenantMiddleware(get_response=lambda r: HttpResponse())
        request = rf.get("/")
        request.user = MagicMock()
        request.user.is_authenticated = True
        request.user.tenant_id = None
        mw.process_request(request)
        assert request.tenant is None

    def test_tenant_ativo_injetado(self, rf, admin_user, tenant):
        mw = CoreTenantMiddleware(get_response=lambda r: HttpResponse())
        request = _auth_request(rf, admin_user)
        mw.process_request(request)
        assert request.tenant == tenant

    def test_tenant_suspenso_faz_logout_e_redireciona(self, rf, admin_user, tenant):
        tenant.status = "suspended"
        tenant.save(update_fields=["status"])

        mw = CoreTenantMiddleware(get_response=lambda r: HttpResponse())
        request = _auth_request(rf, admin_user)
        # Adiciona session mock para logout funcionar
        request.session = MagicMock()

        with patch("apps.core.middleware.logout") as mock_logout:
            response = mw.process_request(request)

        mock_logout.assert_called_once_with(request)
        assert response is not None
        assert response.status_code == 302
        assert "reason=tenant_inactive" in response.url

        # Restaura status
        tenant.status = "active"
        tenant.save(update_fields=["status"])

    def test_tenant_cancelado_faz_logout_e_redireciona(self, rf, admin_user, tenant):
        tenant.status = "cancelled"
        tenant.save(update_fields=["status"])

        mw = CoreTenantMiddleware(get_response=lambda r: HttpResponse())
        request = _auth_request(rf, admin_user)
        request.session = MagicMock()

        with patch("apps.core.middleware.logout") as mock_logout:
            response = mw.process_request(request)

        mock_logout.assert_called_once()
        assert response is not None

        tenant.status = "active"
        tenant.save(update_fields=["status"])

    def test_tenant_inativo_seta_none(self, rf, admin_user, tenant):
        """Tenant com is_active=False → request.tenant permanece None."""
        tenant.is_active = False
        tenant.save(update_fields=["is_active"])

        mw = CoreTenantMiddleware(get_response=lambda r: HttpResponse())
        request = _auth_request(rf, admin_user)
        mw.process_request(request)
        assert request.tenant is None

        tenant.is_active = True
        tenant.save(update_fields=["is_active"])


# ── TimezoneMiddleware ────────────────────────────────────────────────────────


class TestTimezoneMiddleware:
    def test_anonimo_desativa_timezone(self, rf):
        mw = TimezoneMiddleware(get_response=lambda r: HttpResponse())
        request = _anon_request(rf)

        with patch("apps.core.middleware.timezone.deactivate") as mock_deactivate:
            mw.process_request(request)
        mock_deactivate.assert_called()

    def test_usuario_com_timezone_valido(self, rf, admin_user):
        mw = TimezoneMiddleware(get_response=lambda r: HttpResponse())
        request = _auth_request(rf, admin_user)
        admin_user.timezone = "America/Sao_Paulo"

        with patch("apps.core.middleware.timezone.activate") as mock_activate:
            mw.process_request(request)
        mock_activate.assert_called_once()

    def test_usuario_sem_timezone_usa_tenant(self, rf, admin_user, tenant):
        mw = TimezoneMiddleware(get_response=lambda r: HttpResponse())
        request = _auth_request(rf, admin_user)
        request.tenant = tenant
        admin_user.timezone = None

        # Simula tenant com timezone
        tenant_mock = MagicMock()
        tenant_mock.timezone = "America/Manaus"
        request.tenant = tenant_mock

        with patch("apps.core.middleware.timezone.activate") as mock_activate:
            mw.process_request(request)
        mock_activate.assert_called_once()

    def test_timezone_invalido_desativa(self, rf, admin_user):
        mw = TimezoneMiddleware(get_response=lambda r: HttpResponse())
        request = _auth_request(rf, admin_user)
        admin_user.timezone = "Invalid/Timezone"

        with patch("apps.core.middleware.timezone.deactivate") as mock_deactivate:
            mw.process_request(request)
        mock_deactivate.assert_called()

    def test_usuario_sem_timezone_e_sem_tenant_desativa(self, rf, admin_user):
        mw = TimezoneMiddleware(get_response=lambda r: HttpResponse())
        request = _auth_request(rf, admin_user)
        admin_user.timezone = None
        request.tenant = None

        with patch("apps.core.middleware.timezone.deactivate") as mock_deactivate:
            mw.process_request(request)
        mock_deactivate.assert_called()


# ── LastSeenMiddleware ────────────────────────────────────────────────────────


class TestLastSeenMiddleware:
    def test_anonimo_nao_atualiza(self, rf):
        mw = LastSeenMiddleware(get_response=lambda r: HttpResponse())
        request = _anon_request(rf)

        with patch("django.core.cache.cache") as mock_cache:
            mw.process_request(request)
        mock_cache.get.assert_not_called()

    def test_cache_hit_nao_faz_update(self, rf, admin_user):
        mw = LastSeenMiddleware(get_response=lambda r: HttpResponse())
        request = _auth_request(rf, admin_user)

        with patch("django.core.cache.cache") as mock_cache:
            mock_cache.get.return_value = True  # cache hit
            mw.process_request(request)

        # Não deve tentar UPDATE no banco
        mock_cache.set.assert_not_called()

    def test_cache_miss_faz_update_e_seta_cache(self, rf, admin_user):
        mw = LastSeenMiddleware(get_response=lambda r: HttpResponse())
        request = _auth_request(rf, admin_user)

        with patch("django.core.cache.cache") as mock_cache:
            mock_cache.get.return_value = None  # cache miss

            with patch.object(
                type(admin_user).objects,
                "filter",
                return_value=MagicMock(update=MagicMock()),
            ):
                mw.process_request(request)

            mock_cache.set.assert_called_once()
            cache_key = mock_cache.set.call_args[0][0]
            assert str(admin_user.pk) in cache_key

    def test_erro_no_update_ainda_seta_cache(self, rf, admin_user):
        """Mesmo com erro no UPDATE, o cache deve ser marcado (finally block)."""
        mw = LastSeenMiddleware(get_response=lambda r: HttpResponse())
        request = _auth_request(rf, admin_user)

        with patch("django.core.cache.cache") as mock_cache:
            mock_cache.get.return_value = None

            with patch.object(
                type(admin_user).objects,
                "filter",
                side_effect=Exception("DB error"),
            ):
                mw.process_request(request)

            # O finally garante que o cache é setado mesmo com erro
            mock_cache.set.assert_called_once()

    def test_cache_key_inclui_user_id(self, rf, admin_user):
        mw = LastSeenMiddleware(get_response=lambda r: HttpResponse())
        key = mw._cache_key(admin_user.pk)
        assert str(admin_user.pk) in key
        assert "last_seen" in key

    def test_intervalo_de_5_minutos(self):
        mw = LastSeenMiddleware(get_response=lambda r: HttpResponse())
        assert mw.UPDATE_INTERVAL.total_seconds() == 300


# ── SecurityHeadersMiddleware ─────────────────────────────────────────────────


class TestSecurityHeadersMiddleware:
    def _get_response(self, request):
        return HttpResponse("ok")

    def test_adiciona_x_content_type_options(self, rf):
        mw = SecurityHeadersMiddleware(get_response=lambda r: HttpResponse())
        request = rf.get("/")
        response = HttpResponse()
        result = mw.process_response(request, response)
        assert result["X-Content-Type-Options"] == "nosniff"

    def test_adiciona_x_frame_options(self, rf):
        mw = SecurityHeadersMiddleware(get_response=lambda r: HttpResponse())
        request = rf.get("/")
        response = HttpResponse()
        result = mw.process_response(request, response)
        assert result["X-Frame-Options"] == "DENY"

    def test_adiciona_referrer_policy(self, rf):
        mw = SecurityHeadersMiddleware(get_response=lambda r: HttpResponse())
        request = rf.get("/")
        response = HttpResponse()
        result = mw.process_response(request, response)
        assert result["Referrer-Policy"] == "strict-origin-when-cross-origin"

    def test_adiciona_permissions_policy(self, rf):
        mw = SecurityHeadersMiddleware(get_response=lambda r: HttpResponse())
        request = rf.get("/")
        response = HttpResponse()
        result = mw.process_response(request, response)
        assert "camera=()" in result["Permissions-Policy"]
        assert "microphone=()" in result["Permissions-Policy"]

    def test_adiciona_server_header(self, rf):
        mw = SecurityHeadersMiddleware(get_response=lambda r: HttpResponse())
        request = rf.get("/")
        response = HttpResponse()
        result = mw.process_response(request, response)
        assert result["Server"] == "SafraLog"

    def test_retorna_response(self, rf):
        mw = SecurityHeadersMiddleware(get_response=lambda r: HttpResponse())
        request = rf.get("/")
        response = HttpResponse("test")
        result = mw.process_response(request, response)
        assert result is response


# ── TenantMiddleware (apps/tenants/middleware.py) ─────────────────────────────


class TestTenantsTenantMiddleware:
    def _make_middleware(self):
        get_response = MagicMock(return_value=HttpResponse("ok"))
        return TenantsTenantMiddleware(get_response), get_response

    def test_anonimo_retorna_none(self, rf):
        from apps.tenants.middleware import get_tenant

        request = _anon_request(rf)
        assert get_tenant(request) is None

    def test_autenticado_sem_tenant_id_retorna_none(self, rf):
        from apps.tenants.middleware import get_tenant

        request = rf.get("/")
        request.user = MagicMock()
        request.user.is_authenticated = True
        request.user.tenant_id = None
        assert get_tenant(request) is None

    def test_autenticado_com_tenant_retorna_tenant(self, rf, admin_user, tenant):
        from apps.tenants.middleware import get_tenant

        request = _auth_request(rf, admin_user)
        result = get_tenant(request)
        assert result == tenant

    def test_tenant_inexistente_retorna_none(self, rf, admin_user):
        from apps.tenants.middleware import get_tenant

        request = _auth_request(rf, admin_user)
        admin_user.tenant_id = 99999999
        result = get_tenant(request)
        assert result is None

    def test_chama_get_response(self, rf):
        mw, get_response = self._make_middleware()
        request = _anon_request(rf)
        mw(request)
        get_response.assert_called_once_with(request)

    def test_request_tem_atributo_tenant(self, rf, admin_user, tenant):
        mw, _ = self._make_middleware()
        request = _auth_request(rf, admin_user)
        mw(request)
        assert hasattr(request, "tenant")

    def test_lazy_evaluation(self, rf, admin_user, tenant):
        from django.utils.functional import SimpleLazyObject

        mw, _ = self._make_middleware()
        request = _auth_request(rf, admin_user)
        mw(request)
        assert isinstance(request.tenant, SimpleLazyObject)
