"""
SafraLog — apps/tenants/models.py
Model de Tenant (empresa/fazenda) para suporte SaaS multi-tenant.
"""

import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords


class Tenant(models.Model):
    """
    Tenant = empresa/fazenda que usa o SafraLog.
    Todas as models do sistema se relacionam ao Tenant.
    """

    class Plan(models.TextChoices):
        FREE = "free", _("Gratuito")
        STARTER = "starter", _("Starter")
        PROFESSIONAL = "professional", _("Profissional")
        ENTERPRISE = "enterprise", _("Enterprise")

    class Status(models.TextChoices):
        ACTIVE = "active", _("Ativo")
        SUSPENDED = "suspended", _("Suspenso")
        CANCELLED = "cancelled", _("Cancelado")
        TRIAL = "trial", _("Período de teste")

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    name = models.CharField(
        max_length=200,
        verbose_name=_("Nome da empresa"),
    )
    slug = models.SlugField(
        max_length=100,
        unique=True,
        verbose_name=_("Identificador único"),
        help_text=_("Usado na URL. Ex: fazenda-sao-jose"),
    )
    document = models.CharField(
        max_length=18,
        blank=True,
        default="",
        verbose_name=_("CNPJ / CPF"),
    )
    logo = models.ImageField(
        upload_to="tenants/logos/%Y/",
        blank=True,
        null=True,
        verbose_name=_("Logo"),
    )
    plan = models.CharField(
        max_length=20,
        choices=Plan.choices,
        default=Plan.FREE,
        verbose_name=_("Plano"),
        db_index=True,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.TRIAL,
        verbose_name=_("Status"),
        db_index=True,
    )
    # Configurações da fazenda
    timezone = models.CharField(
        max_length=50,
        default="America/Sao_Paulo",
        verbose_name=_("Fuso horário"),
    )
    # Contato
    phone = models.CharField(
        max_length=20,
        blank=True,
        default="",
        verbose_name=_("Telefone"),
    )
    email = models.EmailField(
        blank=True,
        default="",
        verbose_name=_("E-mail"),
    )
    # Controle
    trial_ends_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Fim do período de teste"),
    )
    max_users = models.PositiveIntegerField(
        default=5,
        verbose_name=_("Máximo de usuários"),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = _("Empresa / Fazenda")
        verbose_name_plural = _("Empresas / Fazendas")
        ordering = ["name"]
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["status", "is_active"]),
        ]

    def __str__(self):
        return self.name

    @property
    def is_trial(self):
        return self.status == self.Status.TRIAL

    @property
    def is_suspended(self):
        return self.status == self.Status.SUSPENDED
