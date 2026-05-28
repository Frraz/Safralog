"""
SafraLog — apps/notifications/tasks.py
Tarefas Celery periódicas para alertas automáticos.

Schedule configurado em config/settings/base.py → CELERY_BEAT_SCHEDULE.
"""

from __future__ import annotations

import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(name="notifications.check_cnh_expiry", bind=True, max_retries=3)
def check_cnh_expiry(self):
    """
    Verifica motoristas com CNH vencendo em ≤30 dias.
    Executada diariamente às 7h pelo Celery Beat.
    """
    from apps.accounts.models import User
    from apps.logistics.models import Driver
    from apps.notifications.models import Notification

    today = timezone.localdate()
    alert_date = today + timedelta(days=30)

    drivers = Driver.objects.filter(
        is_active=True,
        status="active",
        cnh_expiry__lte=alert_date,
        cnh_expiry__gte=today,
    ).select_related("tenant")

    # Cache de admins por tenant para evitar N+1 de queries
    admins_by_tenant: dict = {}

    created_count = 0

    for driver in drivers:
        if not driver.cnh_expiry:
            continue

        tenant_id = driver.tenant_id

        if tenant_id not in admins_by_tenant:
            admins_by_tenant[tenant_id] = list(
                User.objects.filter(
                    tenant=driver.tenant,
                    is_active=True,
                    role__in=("admin", "manager"),
                )
            )

        admins = admins_by_tenant[tenant_id]
        if not admins:
            continue

        days_left = (driver.cnh_expiry - today).days
        plural = "s" if days_left != 1 else ""
        title = f"CNH vencendo — {driver.name}"
        message = (
            f"A CNH de {driver.name} vence em {days_left} dia{plural} "
            f"({driver.cnh_expiry:%d/%m/%Y}). Providencie a renovação."
        )

        for user in admins:
            # Deduplicação: uma notificação por (usuário, título) por dia
            already_notified = Notification.objects.filter(
                user=user,
                tenant=driver.tenant,
                title=title,
                created_at__date=today,
            ).exists()

            if already_notified:
                continue

            Notification.notify(
                user=user,
                tenant=driver.tenant,
                title=title,
                message=message,
                level=Notification.Level.WARNING,
                action_url=f"/logistica/motoristas/{driver.pk}/",
                action_label="Ver motorista",
            )
            created_count += 1

    logger.info("check_cnh_expiry: %d notificações criadas", created_count)
    return {"created": created_count}


@shared_task(name="notifications.check_negative_balances", bind=True, max_retries=3)
def check_negative_balances(self):
    """
    Verifica motoristas com saldo negativo.
    Executada diariamente às 6h pelo Celery Beat.
    """
    from apps.accounts.models import User
    from apps.finance.models import FinancialAccount
    from apps.notifications.models import Notification

    today = timezone.localdate()

    accounts = FinancialAccount.objects.filter(
        is_active=True,
        account_type=FinancialAccount.AccountType.DRIVER,
    ).select_related("tenant")

    # Cache de admins por tenant para evitar N+1 de queries
    admins_by_tenant: dict = {}

    # Guard contra contas diferentes do mesmo motorista gerarem notif duplicada
    # Ex: dois registros de FinancialAccount para o mesmo driver no mesmo tenant
    seen: set[tuple] = set()  # (tenant_id, title)

    created_count = 0

    for account in accounts:
        balance = account.current_balance
        if balance >= 0:
            continue

        tenant_id = account.tenant_id
        linked = account.linked_object
        name = getattr(linked, "name", None) or account.name
        title = f"Saldo negativo — {name}"

        # Deduplicação em memória — mesmo motorista com 2 contas não gera 2 notifs
        dedup_key = (tenant_id, title)
        if dedup_key in seen:
            continue
        seen.add(dedup_key)

        if tenant_id not in admins_by_tenant:
            admins_by_tenant[tenant_id] = list(
                User.objects.filter(
                    tenant=account.tenant,
                    is_active=True,
                    role__in=("admin", "manager"),
                )
            )

        admins = admins_by_tenant[tenant_id]
        if not admins:
            continue

        message = (
            f"{name} está com saldo negativo de R$ {abs(balance):.2f}. "
            "Verifique os lançamentos ou realize um acerto."
        )

        for user in admins:
            # Deduplicação no banco — protege contra execução dupla da task
            already_notified = Notification.objects.filter(
                user=user,
                tenant=account.tenant,
                title=title,
                created_at__date=today,
            ).exists()

            if already_notified:
                continue

            Notification.notify(
                user=user,
                tenant=account.tenant,
                title=title,
                message=message,
                level=Notification.Level.ERROR,
                action_url="/financeiro/acertos/novo/",
                action_label="Criar acerto",
            )
            created_count += 1

    logger.info("check_negative_balances: %d notificações criadas", created_count)
    return {"created": created_count}
