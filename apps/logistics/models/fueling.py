"""
SafraLog — apps/logistics/models/fueling.py
ABASTECIMENTO — gera débito no ledger do motorista.
"""
from decimal import Decimal

from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import AuditedModel, NoteModel


class Fueling(AuditedModel, NoteModel):
    """
    Registro de abastecimento de veículo.
    Gera automaticamente uma entrada de débito no ledger do motorista.
    """

    class FuelType(models.TextChoices):
        DIESEL_S10 = "diesel_s10", _("Diesel S10")
        DIESEL_S500 = "diesel_s500", _("Diesel S500")
        GASOLINE = "gasoline", _("Gasolina")
        ETHANOL = "ethanol", _("Etanol")
        ARLA = "arla", _("ARLA 32")

    class PaymentMethod(models.TextChoices):
        DRIVER_ACCOUNT = "driver_account", _("Débito na conta do motorista")
        COMPANY = "company", _("Empresa (sem desconto)")
        CASH = "cash", _("Dinheiro")

    fueling_date = models.DateField(
        verbose_name=_("Data"),
        db_index=True,
    )
    driver = models.ForeignKey(
        "logistics.Driver",
        on_delete=models.PROTECT,
        related_name="fuelings",
        verbose_name=_("Motorista"),
    )
    vehicle = models.ForeignKey(
        "logistics.Vehicle",
        on_delete=models.PROTECT,
        related_name="fuelings",
        verbose_name=_("Veículo"),
    )
    harvest = models.ForeignKey(
        "operations.Harvest",
        on_delete=models.PROTECT,
        related_name="fuelings",
        null=True,
        blank=True,
        verbose_name=_("Safra"),
    )

    fuel_type = models.CharField(
        max_length=20,
        choices=FuelType.choices,
        default=FuelType.DIESEL_S10,
        verbose_name=_("Tipo combustível"),
    )
    liters = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        verbose_name=_("Litros"),
    )
    posted_price_per_liter = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        null=True,
        blank=True,
        verbose_name=_("Preço do posto (R$/L)"),
        help_text=_("Valor real cobrado pelo posto. Deixe em branco se igual ao desconto."),
    )
    driver_price_per_liter = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        verbose_name=_("Preço descontado do motorista (R$/L)"),
        help_text=_("Valor efetivamente descontado do motorista. Pode ser menor que o valor do posto."),
    )
    extras_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0"),
        verbose_name=_("Outros produtos no cupom (R$)"),
        help_text=_("Valor total de outros produtos comprados no mesmo cupom (ex.: ARLA 32, lubrificantes)."),
    )

    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        default=PaymentMethod.DRIVER_ACCOUNT,
        verbose_name=_("Forma de pagamento"),
    )

    odometer = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_("Hodômetro (km)"),
    )

    # Posto / local
    station_name = models.CharField(
        max_length=200,
        blank=True,
        default="",
        verbose_name=_("Posto / Local"),
    )

    # Ledger entry gerada automaticamente
    ledger_entry = models.OneToOneField(
        "finance.LedgerEntry",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="fueling",
        verbose_name=_("Entrada no ledger"),
    )


    class Meta(AuditedModel.Meta):
        verbose_name = _("Abastecimento")
        verbose_name_plural = _("Abastecimentos")
        ordering = ["-fueling_date", "-created_at"]
        indexes = [
            models.Index(fields=["driver", "fueling_date"]),
            models.Index(fields=["vehicle", "fueling_date"]),
            models.Index(fields=["harvest"]),
            models.Index(fields=["payment_method"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(liters__gt=0),
                name="fueling_liters_positive",
            ),
            models.CheckConstraint(
                condition=models.Q(driver_price_per_liter__gt=0),
                name="fueling_driver_price_positive",
            ),
            models.CheckConstraint(
                condition=models.Q(extras_amount__gte=0),
                name="fueling_extras_non_negative",
            ),
        ]

    def __str__(self):
        return (
            f"Abast. {self.driver} | {self.vehicle} | "
            f"{self.liters}L {self.get_fuel_type_display()} | {self.fueling_date}"
        )

    @property
    def driver_debit_total(self) -> Decimal:
        """Valor total descontado do motorista (combustível × preço motorista + extras)."""
        fuel_cost = (self.liters * self.driver_price_per_liter).quantize(Decimal("0.01"))
        extras = (self.extras_amount or Decimal("0")).quantize(Decimal("0.01"))
        return fuel_cost + extras

    @property
    def total_value(self) -> Decimal:
        """Alias de driver_debit_total — mantido para compatibilidade com ledger existente."""
        return self.driver_debit_total

    @property
    def posted_total(self) -> Decimal | None:
        """Valor total real do posto (se informado)."""
        if self.posted_price_per_liter is None:
            return None
        return (self.liters * self.posted_price_per_liter).quantize(Decimal("0.01"))

    @property
    def price_difference_per_liter(self) -> Decimal | None:
        """Diferença entre preço do posto e preço descontado (subsídio por litro)."""
        if self.posted_price_per_liter is None:
            return None
        return (self.posted_price_per_liter - self.driver_price_per_liter).quantize(Decimal("0.0001"))

    @property
    def generates_debit(self) -> bool:
        """Só gera débito no motorista se pagamento for via conta."""
        return self.payment_method == self.PaymentMethod.DRIVER_ACCOUNT
