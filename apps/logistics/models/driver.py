"""
SafraLog — apps/logistics/models/driver.py
"""
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import AuditedModel, NoteModel


class Driver(AuditedModel, NoteModel):
    """
    Motorista vinculado ao tenant.
    """

    class Status(models.TextChoices):
        ACTIVE = "active", _("Ativo")
        INACTIVE = "inactive", _("Inativo")
        ON_LEAVE = "on_leave", _("Em afastamento")

    name = models.CharField(
        max_length=200,
        verbose_name=_("Nome"),
        db_index=True,
    )
    document_cpf = models.CharField(
        max_length=14,
        blank=True,
        default="",
        verbose_name=_("CPF"),
    )
    document_cnh = models.CharField(
        max_length=20,
        blank=True,
        default="",
        verbose_name=_("CNH"),
    )
    cnh_category = models.CharField(
        max_length=5,
        blank=True,
        default="",
        verbose_name=_("Categoria CNH"),
    )
    cnh_expiry = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("Validade CNH"),
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        default="",
        verbose_name=_("Telefone"),
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        verbose_name=_("Status"),
        db_index=True,
    )
    photo = models.ImageField(
        upload_to="drivers/photos/%Y/%m/",
        blank=True,
        null=True,
        verbose_name=_("Foto"),
    )

    # Conta financeira vinculada (para ledger)
    financial_account = models.OneToOneField(
        "finance.FinancialAccount",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="driver",
        verbose_name=_("Conta financeira"),
    )


    class Meta(AuditedModel.Meta):
        verbose_name = _("Motorista")
        verbose_name_plural = _("Motoristas")
        ordering = ["name"]
        indexes = [
            models.Index(fields=["tenant", "status"]),
            models.Index(fields=["name"]),
        ]

    def __str__(self):
        return self.name

    @property
    def is_active_driver(self) -> bool:
        return self.status == self.Status.ACTIVE
