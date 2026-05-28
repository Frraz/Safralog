"""
SafraLog — apps/operations/models/harvest.py
Modelo Harvest (Safra) e Field (Talhão).
"""

from __future__ import annotations

from decimal import Decimal

from django.db import models, transaction

from apps.core.models import AuditedModel


class Harvest(AuditedModel):
    """
    Safra agrícola — entidade raiz que agrupa todas as operações de um ciclo.

    Regras de negócio
    -----------------
    * Apenas uma safra pode estar 'active' por tenant (constraint + método activate()).
    * Transições de status devem usar os métodos activate() / complete() / cancel()
      em vez de atribuir harvest.status diretamente — isso garante atomicidade e
      evita o IntegrityError da UniqueConstraint.
    """

    class Status(models.TextChoices):
        PLANNING = "planning", "Em planejamento"
        ACTIVE = "active", "Ativa"
        COMPLETED = "completed", "Concluída"
        CANCELLED = "cancelled", "Cancelada"

    class CropType(models.TextChoices):
        SOYBEAN = "soybean", "Soja"
        CORN = "corn", "Milho"
        COTTON = "cotton", "Algodão"
        SUGARCANE = "sugarcane", "Cana-de-açúcar"
        COFFEE = "coffee", "Café"
        RICE = "rice", "Arroz"
        WHEAT = "wheat", "Trigo"
        OTHER = "other", "Outro"

    name = models.CharField("Nome", max_length=200)
    crop_type = models.CharField(
        "Cultura principal",
        max_length=20,
        choices=CropType.choices,
        default=CropType.SOYBEAN,
    )
    status = models.CharField(
        "Status",
        max_length=20,
        choices=Status.choices,
        default=Status.PLANNING,
        db_index=True,
    )
    start_date = models.DateField("Data de início")
    end_date = models.DateField("Data de término", null=True, blank=True)

    expected_area_ha = models.DecimalField(
        "Área esperada (ha)",
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    expected_yield_ton_ha = models.DecimalField(
        "Produtividade esperada (ton/ha)",
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
    )
    notes = models.TextField("Observações", blank=True)

    class Meta:
        verbose_name = "Safra"
        verbose_name_plural = "Safras"
        ordering = ["-start_date"]
        indexes = [
            models.Index(fields=["tenant", "status"]),
            models.Index(fields=["tenant", "start_date"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant"],
                condition=models.Q(status="active"),
                name="unique_active_harvest_per_tenant",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.get_crop_type_display()}) — {self.get_status_display()}"

    # ── Status checks ─────────────────────────────────────────────────────────

    @property
    def is_active(self) -> bool:
        return self.status == self.Status.ACTIVE

    @property
    def is_planning(self) -> bool:
        return self.status == self.Status.PLANNING

    @property
    def is_completed(self) -> bool:
        return self.status == self.Status.COMPLETED

    @property
    def is_cancelled(self) -> bool:
        return self.status == self.Status.CANCELLED

    # ── Business logic — status transitions ───────────────────────────────────

    def activate(self) -> None:
        """
        Ativa esta safra atomicamente.

        Antes de ativar, conclui automaticamente qualquer outra safra ativa
        do mesmo tenant usando SELECT FOR UPDATE para evitar race conditions.
        Evita o IntegrityError da constraint unique_active_harvest_per_tenant.
        """
        with transaction.atomic():
            # Bloqueia e conclui qualquer outra safra ativa deste tenant
            (
                Harvest.objects.filter(tenant=self.tenant, status=self.Status.ACTIVE)
                .exclude(pk=self.pk)
                .select_for_update()
                .update(status=self.Status.COMPLETED)
            )
            self.status = self.Status.ACTIVE
            self.save(update_fields=["status", "updated_at"])

    def complete(self) -> None:
        """Conclui esta safra."""
        self.status = self.Status.COMPLETED
        self.save(update_fields=["status", "updated_at"])

    def cancel(self) -> None:
        """Cancela esta safra."""
        self.status = self.Status.CANCELLED
        self.save(update_fields=["status", "updated_at"])

    # ── Computed properties ───────────────────────────────────────────────────

    @property
    def target_production(self) -> Decimal | None:
        """
        Produção-alvo em toneladas (área × produtividade esperada).
        Retorna Decimal para preservar precisão em cálculos financeiros.
        """
        if self.expected_area_ha and self.expected_yield_ton_ha:
            return (self.expected_area_ha * self.expected_yield_ton_ha).quantize(Decimal("0.01"))
        return None

    @property
    def expected_total_tons(self) -> float | None:
        """Alias float de target_production — mantido por compatibilidade."""
        t = self.target_production
        return float(t) if t is not None else None

    @property
    def duration_days(self) -> int | None:
        """Duração em dias (início → término). None se end_date não definido."""
        if self.end_date:
            return (self.end_date - self.start_date).days
        return None


class Field(AuditedModel):
    """
    Talhão agrícola — subdivisão de uma fazenda associada a uma safra.
    """

    region = models.ForeignKey(
        "operations.Region",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="fields",
        verbose_name="Região",
    )
    harvest = models.ForeignKey(
        Harvest,
        on_delete=models.PROTECT,
        related_name="fields",
        verbose_name="Safra",
    )
    name = models.CharField("Nome do talhão", max_length=200)
    area_ha = models.DecimalField(
        "Área (ha)",
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    location_description = models.CharField(
        "Localização / Referência",
        max_length=300,
        blank=True,
    )
    latitude = models.DecimalField(
        "Latitude",
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
    )
    longitude = models.DecimalField(
        "Longitude",
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
    )
    notes = models.TextField("Observações", blank=True)

    class Meta:
        verbose_name = "Talhão"
        verbose_name_plural = "Talhões"
        ordering = ["name"]
        unique_together = [["tenant", "harvest", "name"]]
        indexes = [
            models.Index(fields=["tenant", "harvest"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} — {self.harvest.name}"

    @property
    def has_gps(self) -> bool:
        """True se o talhão tem coordenadas GPS definidas."""
        return self.latitude is not None and self.longitude is not None
