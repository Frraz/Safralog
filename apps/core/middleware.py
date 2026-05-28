"""
SafraLog — apps/core/middleware.py
Middlewares globais.
"""

from __future__ import annotations

import logging
import zoneinfo
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import logout
from django.http import HttpRequest, HttpResponse
from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)


class TenantMiddleware(MiddlewareMixin):
    """
    Injeta request.tenant a partir do usuário autenticado.

    Usa tenant_id (campo FK, sem query) para checar existência antes
    de acessar o objeto. O Django cacheia o acesso à FK na instância
    do User — portanto a query ao banco ocorre apenas uma vez por
    request, mesmo que request.user.tenant seja acessado múltiplas
    vezes (ex: middleware + context processor).
    """

    def process_request(self, request: HttpRequest) -> HttpResponse | None:
        request.tenant = None

        if not request.user.is_authenticated:
            return None

        # tenant_id é o campo FK bruto — zero queries ao banco
        tenant_id = getattr(request.user, "tenant_id", None)
        if tenant_id is None:
            # Superusuários do Django Admin podem não ter tenant
            return None

        # Uma única query — resultado cacheado na instância do User pelo Django ORM
        tenant = request.user.tenant

        if not tenant or not tenant.is_active:
            logger.warning(
                "Tenant inativo ou ausente para usuário %s",
                request.user.email,
            )
            return None

        if tenant.status in ("suspended", "cancelled"):
            logger.warning(
                "Tenant %s com status '%s' — forçando logout do usuário %s",
                tenant.slug,
                tenant.status,
                request.user.email,
            )
            logout(request)
            from django.shortcuts import redirect

            return redirect(f"{settings.LOGIN_URL}?reason=tenant_inactive")

        request.tenant = tenant
        return None


class TimezoneMiddleware(MiddlewareMixin):
    """
    Ativa o timezone do usuário (ou do tenant) para cada request.
    Fallback para UTC quando timezone não está configurado ou é inválido.

    Ordem de precedência:
      1. request.user.timezone  (preferência individual)
      2. request.tenant.timezone (configuração da fazenda)
      3. UTC (deactivate())
    """

    def process_request(self, request: HttpRequest) -> None:
        tz_name: str | None = None

        if request.user.is_authenticated:
            tz_name = getattr(request.user, "timezone", None) or None
            if not tz_name and getattr(request, "tenant", None):
                tz_name = getattr(request.tenant, "timezone", None) or None

        if tz_name:
            try:
                timezone.activate(zoneinfo.ZoneInfo(tz_name))
            except (zoneinfo.ZoneInfoNotFoundError, ValueError):
                logger.warning(
                    "Timezone inválido '%s' para usuário %s — usando UTC",
                    tz_name,
                    getattr(request.user, "email", "anônimo"),
                )
                timezone.deactivate()
        else:
            timezone.deactivate()


class LastSeenMiddleware(MiddlewareMixin):
    """
    Atualiza User.last_seen_at no máximo 1x a cada 5 minutos.

    USA CACHE (não session).

    Motivo: o allauth chama session.cycle_key() no login para prevenir
    session fixation — isso invalida a session antiga. Qualquer escrita
    em request.session antes disso resulta em UpdateError →
    SessionInterrupted → HTTP 400. O cache Django não tem esse problema.

    O cache.set() fica em `finally` para garantir que seja executado
    mesmo quando o UPDATE falha (ex: campo inexistente em teste,
    permissão negada, etc.) — sem isso, toda request tenta de novo e
    loga "Falha silenciosa" repetidamente.
    """

    UPDATE_INTERVAL = timedelta(minutes=5)

    def _cache_key(self, user_id) -> str:
        return f"safralog:last_seen:{user_id}"

    def process_request(self, request: HttpRequest) -> None:
        if not request.user.is_authenticated:
            return

        from django.core.cache import cache

        cache_key = self._cache_key(request.user.pk)

        # Saída rápida — sem query ao banco
        if cache.get(cache_key):
            return

        try:
            type(request.user).objects.filter(pk=request.user.pk).update(
                last_seen_at=timezone.now()
            )
        except Exception:
            logger.debug(
                "Falha ao atualizar last_seen_at para user %s",
                request.user.pk,
            )
        finally:
            # Sempre marca como "visto" — mesmo com erro no UPDATE —
            # para não tentar novamente em todo request subsequente.
            cache.set(
                cache_key,
                True,
                timeout=int(self.UPDATE_INTERVAL.total_seconds()),
            )


class SecurityHeadersMiddleware(MiddlewareMixin):
    """
    Adiciona headers de segurança HTTP em todas as respostas.
    Funciona em dev e prod — não depende de HTTPS.
    """

    def process_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        # Evita MIME type sniffing — crítico para uploads de arquivos
        response["X-Content-Type-Options"] = "nosniff"

        # Evita clickjacking — o sistema não é embutido em iframes
        response["X-Frame-Options"] = "DENY"

        # Controla informação de referrer em navegação cross-origin
        response["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Desativa APIs desnecessárias no browser
        response["Permissions-Policy"] = (
            "camera=(), "
            "microphone=(), "
            "geolocation=(), "
            "payment=(), "
            "usb=(), "
            "interest-cohort=()"  # anti-FLoC
        )

        # Ofusca a versão do servidor (complementa configuração do Nginx)
        response["Server"] = "SafraLog"

        return response
