"""
SafraLog — apps/core/models.py
Modelos base reutilizados por todos os apps.
Toda model do sistema herda de BaseModel ou TenantModel.
"""
import uuid

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords


class BaseModel(models.Model):
    """
    Model base com UUID, timestamps e soft delete.
    Herdar em TODAS as models do sistema.
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_("ID"),
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Criado em"),
        db_index=True,
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Atualizado em"),
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("Ativo"),
        db_index=True,
    )

    class Meta:
        abstract = True
        ordering = ["-created_at"]

    def soft_delete(self):
        """Soft delete — nunca apagar dados reais."""
        self.is_active = False
        self.save(update_fields=["is_active", "updated_at"])

    def restore(self):
        """Restaura registro soft-deleted."""
        self.is_active = True
        self.save(update_fields=["is_active", "updated_at"])


class TenantModel(BaseModel):
    """
    Model com suporte multi-tenant.
    Herdar em TODAS as models que pertencem a um tenant.
    """
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        related_name="%(app_label)s_%(class)s_set",
        verbose_name=_("Empresa"),
        db_index=True,
    )

    class Meta(BaseModel.Meta):
        abstract = True

    def save(self, *args, **kwargs):
        # Garante que tenant está definido antes de salvar
        if not self.tenant_id:
            raise ValueError(
                f"{self.__class__.__name__} requer um tenant definido."
            )
        super().save(*args, **kwargs)


class AuditedModel(TenantModel):
    """
    Model com auditoria completa via django-simple-history.
    Usar em models críticas (financeiro, romaneios, fechamentos).
    """
    history = HistoricalRecords(inherit=True)

    class Meta(TenantModel.Meta):
        abstract = True


class NoteModel(models.Model):
    """
    Mixin para models que suportam observações/notas.
    """
    notes = models.TextField(
        blank=True,
        default="",
        verbose_name=_("Observações"),
    )

    class Meta:
        abstract = True


class AddressModel(models.Model):
    """
    Mixin para models com endereço.
    """
    address_street = models.CharField(
        max_length=200,
        blank=True,
        default="",
        verbose_name=_("Logradouro"),
    )
    address_number = models.CharField(
        max_length=20,
        blank=True,
        default="",
        verbose_name=_("Número"),
    )
    address_complement = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name=_("Complemento"),
    )
    address_neighborhood = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name=_("Bairro"),
    )
    address_city = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name=_("Cidade"),
    )
    address_state = models.CharField(
        max_length=2,
        blank=True,
        default="",
        verbose_name=_("UF"),
    )
    address_zip = models.CharField(
        max_length=9,
        blank=True,
        default="",
        verbose_name=_("CEP"),
    )

    class Meta:
        abstract = True

    @property
    def full_address(self) -> str:
        parts = filter(None, [
            self.address_street,
            self.address_number,
            self.address_complement,
            self.address_neighborhood,
            self.address_city,
            self.address_state,
        ])
        return ", ".join(parts)
