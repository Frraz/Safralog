"""
Context processors globais do SafraLog.
Adicionam variáveis ao contexto de todos os templates.

Registrar em settings.TEMPLATES[0]['OPTIONS']['context_processors'].
"""

from __future__ import annotations

import datetime

from django.conf import settings
from django.http import HttpRequest
from django.utils import timezone


def app_settings(request: HttpRequest) -> dict:
    """
    Expõe configurações básicas do app para os templates.
    """
    return {
        "APP_NAME": getattr(settings, "APP_NAME", "SafraLog"),
        "APP_VERSION": getattr(settings, "APP_VERSION", "1.0.0"),
        "APP_ENV": "production" if not settings.DEBUG else "development",
        "SUPPORT_EMAIL": getattr(settings, "SUPPORT_EMAIL", "suporte@safralog.com.br"),
    }


def tenant_context(request: HttpRequest) -> dict:
    """
    Expõe informações do tenant atual para os templates.
    Requer TenantMiddleware instalado.
    """
    tenant = getattr(request, "tenant", None)

    # "not tenant" avalia corretamente SimpleLazyObject wrapping None
    if not tenant:
        return {"current_tenant": None}

    return {
        "current_tenant": tenant,
        "tenant_name": tenant.name,
        "tenant_plan": tenant.plan,
        "tenant_is_trial": tenant.status == "trial",
        "tenant_trial_ends_at": getattr(tenant, "trial_ends_at", None),
    }


def unread_notifications(request: HttpRequest) -> dict:
    """
    Conta notificações não lidas do usuário.
    Retorna 0 se o usuário não está autenticado ou em caso de erro.

    Lazy: usa cache de sessão para evitar query em todo request.
    """
    if not request.user.is_authenticated:
        return {"unread_notifications_count": 0}

    cache_key = "_unread_notif_count"
    cached = request.session.get(cache_key)

    # Formato: {"count": int, "cached_at": timestamp ISO}
    if cached and isinstance(cached, dict):
        try:
            cached_at = datetime.datetime.fromisoformat(cached["cached_at"]).replace(
                tzinfo=datetime.UTC
            )
            if (timezone.now() - cached_at) < datetime.timedelta(minutes=2):
                return {"unread_notifications_count": cached["count"]}
        except (KeyError, ValueError):
            pass

    try:
        from apps.notifications.models import Notification

        tenant = getattr(request, "tenant", None)
        count = Notification.objects.filter(
            user=request.user,
            is_read=False,
            tenant=tenant if tenant else None,
        ).count()
    except Exception:
        count = 0

    request.session[cache_key] = {
        "count": count,
        "cached_at": timezone.now().isoformat(),
    }

    return {"unread_notifications_count": count}


def active_harvest(request: HttpRequest) -> dict:
    """
    Retorna a safra ativa do tenant atual (se houver).
    Usado na navbar e no dashboard.
    """
    tenant = getattr(request, "tenant", None)

    if not tenant or not request.user.is_authenticated:
        return {"active_harvest": None}

    cache_key = f"_active_harvest_{tenant.pk}"

    try:
        from django.core.cache import cache

        _MISSING = object()
        harvest = cache.get(cache_key, _MISSING)

        if harvest is _MISSING:
            from apps.operations.models import Harvest

            harvest = (
                Harvest.objects.filter(tenant=tenant, status="active")
                .order_by("-start_date")
                .first()
            )
            cache.set(cache_key, harvest, timeout=300)
    except Exception:
        harvest = None

    return {"active_harvest": harvest}
