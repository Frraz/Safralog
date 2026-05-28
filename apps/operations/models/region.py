"""
SafraLog — apps/operations/models/region.py
Região de origem das cargas — define preço padrão por tonelada.
"""
from __future__ import annotations

from decimal import Decimal

from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import AuditedModel


class Region(AuditedModel):
    """
    Região de coleta (fazenda/localidade).
    Determina o valor padrão por tonelada pago ao motorista.

    Exemplos: Miguel Baiano (R$ 80/ton), Rio Duro (R$ 65/ton).
    """

    name = models.CharField(
        "Nome da região",
        max_length=100,
    )
    default_price_per_ton = models.DecimalField(
        "Valor padrão por tonelada (R$)",
        max_digits=10,
        decimal_places=2,
    )
    description = models.TextField(
        "Descrição / Referência",
        blank=True,
        default="",
    )

    class Meta(AuditedModel.Meta):
        verbose_name = "Região"
        verbose_name_plural = "Regiões"
        ordering = ["name"]
        unique_together = [["tenant", "name"]]
        indexes = [
            models.Index(fields=["tenant", "name"]),
        ]

    def __str__(self) -> str:
        price = self.default_price_per_ton
        return f"{self.name} — R$ {price:.2f}/ton"

    @property
    def price_display(self) -> str:
        return f"R$ {self.default_price_per_ton:.2f}"
