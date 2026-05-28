"""
SafraLog — apps/accounts/models.py
User model customizado com suporte multi-tenant e permissões por papel.
"""
import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    """
    User customizado com UUID, telefone e vinculação ao Tenant.
    """

    class Role(models.TextChoices):
        ADMIN = "admin", _("Administrador")
        MANAGER = "manager", _("Gerente")
        OPERATOR = "operator", _("Operador")
        DRIVER = "driver", _("Motorista")
        VIEWER = "viewer", _("Visualizador")

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    email = models.EmailField(
        unique=True,
        verbose_name=_("E-mail"),
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        default="",
        verbose_name=_("Telefone"),
    )
    avatar = models.ImageField(
        upload_to="avatars/%Y/%m/",
        blank=True,
        null=True,
        verbose_name=_("Avatar"),
    )
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.OPERATOR,
        verbose_name=_("Papel"),
        db_index=True,
    )
    # Tenant principal do usuário
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
        verbose_name=_("Empresa"),
    )
    timezone = models.CharField(
        max_length=50,
        default="America/Sao_Paulo",
        verbose_name=_("Fuso horário"),
    )
    is_active = models.BooleanField(default=True)
    last_seen_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Último acesso"),
    )


    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username", "first_name", "last_name"]

    class Meta:
        verbose_name = _("Usuário")
        verbose_name_plural = _("Usuários")
        ordering = ["first_name", "last_name"]

    def __str__(self):
        return self.get_full_name() or self.email

    @property
    def full_name(self):
        return self.get_full_name() or self.email

    @property
    def initials(self):
        parts = self.get_full_name().split()
        if len(parts) >= 2:
            return f"{parts[0][0]}{parts[-1][0]}".upper()
        return self.email[:2].upper()

    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN or self.is_superuser

    @property
    def is_manager(self):
        return self.role in (self.Role.ADMIN, self.Role.MANAGER) or self.is_superuser

    @property
    def is_operator(self):
        return self.role in (self.Role.ADMIN, self.Role.MANAGER, self.Role.OPERATOR) or self.is_superuser

    def can_access_tenant(self, tenant) -> bool:
        """Verifica se usuário pode acessar determinado tenant."""
        if self.is_superuser:
            return True
        return self.tenant_id == tenant.id


class UserTenantMembership(models.Model):
    """
    Permite que um usuário pertença a múltiplos tenants (futuro).
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    role = models.CharField(
        max_length=20,
        choices=User.Role.choices,
        default=User.Role.OPERATOR,
    )
    joined_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = _("Membro do Tenant")
        verbose_name_plural = _("Membros do Tenant")
        unique_together = [("user", "tenant")]
        ordering = ["-joined_at"]

    def __str__(self):
        return f"{self.user} @ {self.tenant}"
