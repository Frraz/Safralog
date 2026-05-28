"""
Modelo de Notificações in-app.
"""
from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.core.models import TenantModel


class Notification(TenantModel):
    """
    Notificação in-app para um usuário.
    Criada por signals ou tasks do Celery.
    """

    class Level(models.TextChoices):
        INFO = "info", "Informação"
        SUCCESS = "success", "Sucesso"
        WARNING = "warning", "Atenção"
        ERROR = "error", "Erro"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
        verbose_name="Usuário",
    )
    title = models.CharField("Título", max_length=200)
    message = models.TextField("Mensagem")
    level = models.CharField(
        "Nível", max_length=10,
        choices=Level.choices, default=Level.INFO,
    )
    is_read = models.BooleanField("Lida", default=False, db_index=True)
    read_at = models.DateTimeField("Lida em", null=True, blank=True)

    # Link opcional para ação
    action_url = models.CharField("URL de ação", max_length=500, blank=True)
    action_label = models.CharField("Label do botão", max_length=100, blank=True)

    class Meta:
        verbose_name = "Notificação"
        verbose_name_plural = "Notificações"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "is_read", "tenant"]),
        ]

    def __str__(self) -> str:
        return f"[{self.level}] {self.title} → {self.user}"

    def mark_as_read(self) -> None:
        if not self.is_read:
            from django.utils import timezone
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=["is_read", "read_at"])

    @classmethod
    def notify(
        cls,
        user,
        title: str,
        message: str,
        level: str = "info",
        action_url: str = "",
        action_label: str = "",
        tenant=None,
    ) -> "Notification":
        """Cria notificação para o usuário."""
        tenant = tenant or getattr(user, "tenant", None)
        return cls.objects.create(
            user=user,
            tenant=tenant,
            title=title,
            message=message,
            level=level,
            action_url=action_url,
            action_label=action_label,
        )
