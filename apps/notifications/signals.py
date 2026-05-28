"""
SafraLog — apps/notifications/signals.py
Cria notificações automaticamente quando eventos importantes ocorrem.
"""

from __future__ import annotations

import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _create_notification(user, title: str, message: str, level: str = "info") -> None:
    """
    Cria uma notificação para o usuário. Nunca propaga exceção ao fluxo principal.

    FIX: o campo do model é `level`, não `notification_type`.
         O campo `title` é obrigatório e estava ausente.
         Usa Notification.notify() para centralizar a criação.
    """
    try:
        from apps.notifications.models import Notification

        Notification.notify(
            user=user,
            title=title,
            message=message,
            level=level,
        )
    except Exception:
        logger.exception("Falha ao criar notificação para user %s", user.pk)


def _notify_admins(tenant, title: str, message: str, level: str = "info") -> None:
    """Notifica todos os admins/managers de um tenant."""
    try:
        from apps.accounts.models import User

        admins = User.objects.filter(
            tenant=tenant,
            is_active=True,
            role__in=("admin", "manager"),
        )
        for user in admins:
            _create_notification(user, title=title, message=message, level=level)
    except Exception:
        logger.exception("Falha ao notificar admins do tenant %s", tenant.pk)


# ── Signals ───────────────────────────────────────────────────────────────────


@receiver(post_save, sender="operations.Waybill")
def waybill_confirmed(sender, instance, created, update_fields, **kwargs):
    """
    Notifica admins ao confirmar romaneio.

    FIX: usa update_fields para evitar notificação duplicada em saves
    que não alteraram o status (ex: ao vincular ledger_entry depois da confirmação).
    """
    if created:
        return

    # Se update_fields foi passado e não inclui "status", o status não mudou
    if update_fields is not None and "status" not in update_fields:
        return

    if instance.status != "confirmed":
        return

    try:
        net_tons = float(instance.net_weight_tons)
        driver_name = instance.driver.name if instance.driver_id else "—"
    except Exception:
        net_tons = 0.0
        driver_name = "—"

    _notify_admins(
        tenant=instance.tenant,
        title=f"Romaneio #{instance.number:05d} confirmado",
        message=(f"Romaneio #{instance.number:05d} confirmado — {driver_name} · {net_tons:.2f} t"),
        level="success",
    )


@receiver(post_save, sender="finance.Settlement")
def settlement_status_changed(sender, instance, created, update_fields, **kwargs):
    """Notifica ao aprovar ou fechar fechamento."""
    if created:
        return

    if update_fields is not None and "status" not in update_fields:
        return

    if instance.status == "approved":
        try:
            acc_name = instance.account.name if instance.account_id else "—"
            net = float(instance.snapshot_net_balance or 0)
        except Exception:
            acc_name = "—"
            net = 0.0

        _notify_admins(
            tenant=instance.tenant,
            title="Acerto aprovado",
            message=f"Acerto aprovado — {acc_name} · R$ {net:.2f} líquido",
            level="success",
        )

    elif instance.status == "closed":
        try:
            acc_name = instance.account.name if instance.account_id else "—"
        except Exception:
            acc_name = "—"

        _notify_admins(
            tenant=instance.tenant,
            title="Acerto fechado",
            message=f"Acerto fechado — {acc_name}",
            level="info",
        )
