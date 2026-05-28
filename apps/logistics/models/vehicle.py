"""
Modelo Vehicle (Veículo).
"""
from __future__ import annotations

from django.db import models

from apps.core.models import AuditedModel


class Vehicle(AuditedModel):
    """
    Veículo de transporte (caminhão, carreta, etc.).
    """

    class VehicleType(models.TextChoices):
        TRUCK = "truck", "Caminhão simples"
        SEMI_TRAILER = "semi_trailer", "Carreta/Bitrem"
        TRACTOR = "tractor", "Trator"
        PICKUP = "pickup", "Camionete"
        OTHER = "other", "Outro"

    class Status(models.TextChoices):
        ACTIVE = "active", "Ativo"
        MAINTENANCE = "maintenance", "Em manutenção"
        INACTIVE = "inactive", "Inativo"

    plate = models.CharField("Placa", max_length=10, db_index=True)
    vehicle_type = models.CharField(
        "Tipo", max_length=20,
        choices=VehicleType.choices, default=VehicleType.TRUCK,
    )
    brand = models.CharField("Marca", max_length=100, blank=True)
    model = models.CharField("Modelo", max_length=100, blank=True)
    year = models.PositiveSmallIntegerField("Ano", null=True, blank=True)
    color = models.CharField("Cor", max_length=50, blank=True)
    status = models.CharField(
        "Status", max_length=20,
        choices=Status.choices, default=Status.ACTIVE,
        db_index=True,
    )

    # Capacidade de carga
    payload_kg = models.PositiveIntegerField(
        "Capacidade de carga (kg)", null=True, blank=True,
    )

    # Proprietário do veículo — quem recebe o pagamento
    proprietario = models.ForeignKey(
        "logistics.Proprietario",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="vehicles",
        verbose_name="Proprietário",
    )

    # Motorista padrão (pode ser sobreescrito no romaneio)
    default_driver = models.ForeignKey(
        "logistics.Driver",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="default_vehicles",
        verbose_name="Motorista padrão",
    )

    notes = models.TextField("Observações", blank=True)


    class Meta:
        verbose_name = "Veículo"
        verbose_name_plural = "Veículos"
        ordering = ["plate"]
        unique_together = [["tenant", "plate"]]

    def __str__(self) -> str:
        model_info = f" {self.brand} {self.model}".strip() if self.brand else ""
        return f"{self.plate}{model_info}"
