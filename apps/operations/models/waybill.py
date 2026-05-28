"""
SafraLog — apps/operations/models/waybill.py
ROMANEIO — documento central da operação de colheita.

Cada viagem gera um romaneio com:
- Talhão de origem
- Motorista / Veículo
- Peso bruto e tara (= peso líquido)
- Cultura transportada
- Preço por tonelada
- Fotos/documentos anexados

Transições de status
--------------------
DRAFT → confirm() → CONFIRMED → (service) → SETTLED
DRAFT | CONFIRMED  → cancel()  → CANCELLED
"""

from decimal import Decimal

from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from apps.core.models import AuditedModel, NoteModel


class Waybill(AuditedModel, NoteModel):
    """Romaneio de transporte / colheita."""

    class Status(models.TextChoices):
        DRAFT = "draft", _("Rascunho")
        CONFIRMED = "confirmed", _("Confirmado")
        SETTLED = "settled", _("Fechado")
        CANCELLED = "cancelled", _("Cancelado")

    class Culture(models.TextChoices):
        SOYBEAN = "soybean", _("Soja")
        CORN = "corn", _("Milho")
        COTTON = "cotton", _("Algodão")
        SUGARCANE = "sugarcane", _("Cana-de-açúcar")
        COFFEE = "coffee", _("Café")
        RICE = "rice", _("Arroz")
        WHEAT = "wheat", _("Trigo")
        OTHER = "other", _("Outro")

    # ── Identificação ─────────────────────────────────────────────────────────

    # Número sequencial por tenant
    number = models.PositiveIntegerField(
        verbose_name=_("Número"),
        db_index=True,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        verbose_name=_("Status"),
        db_index=True,
    )

    # ── Data / hora ───────────────────────────────────────────────────────────

    operation_date = models.DateField(
        verbose_name=_("Data da operação"),
        db_index=True,
    )
    operation_time = models.TimeField(
        verbose_name=_("Hora da operação"),
        null=True,
        blank=True,
    )

    # ── Relações operacionais ─────────────────────────────────────────────────

    harvest = models.ForeignKey(
        "operations.Harvest",
        on_delete=models.PROTECT,
        related_name="waybills",
        verbose_name=_("Safra"),
    )
    field = models.ForeignKey(
        "operations.Field",
        on_delete=models.PROTECT,
        related_name="waybills",
        verbose_name=_("Talhão"),
        null=True,
        blank=True,
    )
    driver = models.ForeignKey(
        "logistics.Driver",
        on_delete=models.PROTECT,
        related_name="waybills",
        verbose_name=_("Motorista"),
    )
    vehicle = models.ForeignKey(
        "logistics.Vehicle",
        on_delete=models.PROTECT,
        related_name="waybills",
        verbose_name=_("Veículo"),
    )

    # ── Carga ─────────────────────────────────────────────────────────────────

    culture = models.CharField(
        max_length=20,
        choices=Culture.choices,
        default=Culture.SOYBEAN,
        verbose_name=_("Cultura"),
    )

    # ── Pesagem ───────────────────────────────────────────────────────────────

    gross_weight = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        verbose_name=_("Peso bruto (kg)"),
    )
    tare_weight = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        verbose_name=_("Tara (kg)"),
    )

    # ── Preço ─────────────────────────────────────────────────────────────────

    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        verbose_name=_("Preço por tonelada (R$)"),
        help_text=_("Valor pago por tonelada transportada"),
    )

    # ── Logística ─────────────────────────────────────────────────────────────

    destination = models.CharField(
        max_length=200,
        blank=True,
        default="",
        verbose_name=_("Destino / Armazém"),
    )
    scale_ticket = models.CharField(
        max_length=50,
        blank=True,
        default="",
        verbose_name=_("Ticket balança"),
        db_index=True,
    )

    # ── Vínculos financeiros ──────────────────────────────────────────────────

    settlement = models.ForeignKey(
        "finance.Settlement",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="waybills",
        verbose_name=_("Fechamento"),
    )
    ledger_entry = models.OneToOneField(
        "finance.LedgerEntry",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="waybill",
        verbose_name=_("Entrada no ledger"),
    )

    # ── Meta ──────────────────────────────────────────────────────────────────

    class Meta(AuditedModel.Meta):
        verbose_name = _("Romaneio")
        verbose_name_plural = _("Romaneios")
        ordering = ["-operation_date", "-number"]
        indexes = [
            models.Index(fields=["tenant", "number"]),
            models.Index(fields=["harvest", "status"]),
            models.Index(fields=["driver", "operation_date"]),
            models.Index(fields=["operation_date"]),
            models.Index(fields=["settlement"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "number"],
                name="waybill_unique_number_per_tenant",
            ),
            models.CheckConstraint(
                condition=models.Q(gross_weight__gt=0),
                name="waybill_gross_weight_positive",
            ),
            models.CheckConstraint(
                condition=models.Q(tare_weight__gte=0),
                name="waybill_tare_weight_non_negative",
            ),
            models.CheckConstraint(
                condition=models.Q(unit_price__gt=0),
                name="waybill_unit_price_positive",
            ),
        ]

    def __str__(self) -> str:
        return f"Romaneio #{self.number:05d} | {self.operation_date}"

    # ── URL canônica ──────────────────────────────────────────────────────────

    def get_absolute_url(self) -> str:
        """
        URL canônica do romaneio.
        Corrige: AttributeError 'Waybill' object has no attribute 'get_absolute_url'
        Permite usar redirect(waybill.get_absolute_url()) nas views e
        {{ waybill.get_absolute_url }} nos templates sem hardcodear a URL.
        """
        return reverse("operations:waybill-detail", kwargs={"pk": self.pk})

    # ── Status checks ─────────────────────────────────────────────────────────

    @property
    def is_draft(self) -> bool:
        return self.status == self.Status.DRAFT

    @property
    def is_confirmed(self) -> bool:
        return self.status == self.Status.CONFIRMED

    @property
    def is_settled(self) -> bool:
        return self.status == self.Status.SETTLED

    @property
    def is_cancelled(self) -> bool:
        return self.status == self.Status.CANCELLED

    @property
    def is_editable(self) -> bool:
        """Apenas rascunhos podem ser editados."""
        return self.status == self.Status.DRAFT

    # ── Business rules ────────────────────────────────────────────────────────

    @property
    def can_confirm(self) -> bool:
        """Pode confirmar somente se estiver em rascunho."""
        return self.status == self.Status.DRAFT

    @property
    def can_cancel(self) -> bool:
        """Pode cancelar rascunhos e confirmados; fechados não."""
        return self.status in (self.Status.DRAFT, self.Status.CONFIRMED)

    # ── Status transitions ────────────────────────────────────────────────────

    def confirm(self, user=None) -> None:
        """
        Confirma o romaneio (DRAFT → CONFIRMED).
        Salva apenas o campo status para evitar sobrescrever outros campos
        em edição concorrente.

        Nota: a geração do LedgerEntry de produção é responsabilidade do
        LedgerService, chamado pela WaybillConfirmView após este método.
        """
        if not self.can_confirm:
            raise ValueError(
                f"Romaneio #{self.number} não pode ser confirmado "
                f"(status atual: {self.get_status_display()})."
            )
        self.status = self.Status.CONFIRMED
        self.save(update_fields=["status", "updated_at"])

    def cancel(self, user=None) -> None:
        """
        Cancela o romaneio (DRAFT | CONFIRMED → CANCELLED).
        Romaneios fechados (SETTLED) não podem ser cancelados — use o
        settlement_service.cancel_settlement() para reverter o fechamento
        e depois cancele os romaneios individualmente.
        """
        if not self.can_cancel:
            raise ValueError(
                f"Romaneio #{self.number} não pode ser cancelado "
                f"(status atual: {self.get_status_display()})."
            )
        self.status = self.Status.CANCELLED
        self.save(update_fields=["status", "updated_at"])

    # ── Computed properties ───────────────────────────────────────────────────

    @property
    def net_weight(self) -> Decimal:
        """Peso líquido em kg = bruto − tara."""
        return self.gross_weight - self.tare_weight

    @property
    def net_weight_tons(self) -> Decimal:
        """Peso líquido em toneladas."""
        return self.net_weight / Decimal("1000")

    @property
    def total_value(self) -> Decimal:
        """Valor total = peso líquido (ton) × preço por tonelada."""
        return (self.net_weight_tons * self.unit_price).quantize(Decimal("0.01"))
