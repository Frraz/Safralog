"""
SafraLog — apps/finance/models/ledger.py
"""

from decimal import Decimal

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models, transaction
from django.db.models import Sum
from django.utils.translation import gettext_lazy as _

from apps.core.models import AuditedModel


class LedgerEntry(AuditedModel):
    """
    Entrada no ledger financeiro.
    IMUTÁVEL após criação — reversões criam novas entradas negativas.
    """

    class EntryType(models.TextChoices):
        WAYBILL_PRODUCTION = "waybill_production", _("Produção — Romaneio")
        ADVANCE_PAYMENT = "advance_payment", _("Adiantamento")
        ADJUSTMENT_CREDIT = "adjustment_credit", _("Ajuste Crédito")
        FUELING_DEBIT = "fueling_debit", _("Abastecimento — Débito")
        ADVANCE_DEBIT = "advance_debit", _("Desconto Adiantamento")
        ADJUSTMENT_DEBIT = "adjustment_debit", _("Ajuste Débito")
        SETTLEMENT_SNAPSHOT = "settlement_snapshot", _("Fechamento — Snapshot")
        REVERSAL = "reversal", _("Estorno")

    class Direction(models.TextChoices):
        CREDIT = "credit", _("Crédito")
        DEBIT = "debit", _("Débito")

    account = models.ForeignKey(
        "finance.FinancialAccount",
        on_delete=models.PROTECT,
        related_name="entries",
        verbose_name=_("Conta"),
    )
    entry_type = models.CharField(
        max_length=30,
        choices=EntryType.choices,
        verbose_name=_("Tipo"),
        db_index=True,
    )
    direction = models.CharField(
        max_length=6,
        choices=Direction.choices,
        verbose_name=_("Direção"),
        db_index=True,
    )
    amount = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        verbose_name=_("Valor (R$)"),
    )
    quantity = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        verbose_name=_("Quantidade (kg/ton)"),
    )
    unit_price = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        verbose_name=_("Preço unitário"),
    )
    competence_date = models.DateField(
        verbose_name=_("Data competência"),
        db_index=True,
    )
    source_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    source_id = models.UUIDField(null=True, blank=True)
    source = GenericForeignKey("source_type", "source_id")
    settlement = models.ForeignKey(
        "finance.Settlement",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ledger_entries",
        verbose_name=_("Fechamento"),
    )
    description = models.TextField(verbose_name=_("Descrição"))
    reference_code = models.CharField(
        max_length=50,
        blank=True,
        default="",
        verbose_name=_("Código referência"),
        db_index=True,
    )
    is_reversed = models.BooleanField(default=False, verbose_name=_("Estornado"))
    reversal_entry = models.OneToOneField(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reversed_entry",
        verbose_name=_("Entrada de estorno"),
    )

    class Meta(AuditedModel.Meta):
        verbose_name = _("Entrada no Ledger")
        verbose_name_plural = _("Entradas no Ledger")
        ordering = ["-competence_date", "-created_at"]
        indexes = [
            models.Index(fields=["account", "direction", "competence_date"]),
            models.Index(fields=["account", "entry_type"]),
            models.Index(fields=["settlement"]),
            models.Index(fields=["source_type", "source_id"]),
            models.Index(fields=["competence_date"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gte=0),
                name="ledger_amount_non_negative",
            ),
        ]

    def __str__(self):
        direction = "+" if self.direction == self.Direction.CREDIT else "-"
        return f"{direction}R$ {self.amount:.2f} | {self.get_entry_type_display()} | {self.competence_date}"

    # FIX: @transaction.atomic garante atomicidade do par (reversal + mark_reversed).
    # Sem isso, se o save() final falhar, o reversal entry existe no banco
    # mas is_reversed=False — estado inconsistente permanente.
    @transaction.atomic
    def create_reversal(self, user=None, reason: str = "") -> "LedgerEntry":
        """
        Cria entrada de estorno (oposta) e marca esta como revertida.
        Ledger é IMUTÁVEL — nunca editar, sempre estornar.
        """
        if self.is_reversed:
            raise ValueError(
                f"LedgerEntry #{self.pk} já foi estornada. Não é possível estornar duas vezes."
            )

        opposite_direction = (
            self.Direction.DEBIT
            if self.direction == self.Direction.CREDIT
            else self.Direction.CREDIT
        )

        description = f"ESTORNO: {self.description}"
        if reason:
            description += f" | Motivo: {reason}"

        reversal = LedgerEntry.objects.create(
            tenant=self.tenant,
            account=self.account,
            entry_type=self.EntryType.REVERSAL,
            direction=opposite_direction,
            amount=self.amount,
            quantity=self.quantity,
            unit_price=self.unit_price,
            competence_date=self.competence_date,
            description=description,
        )

        self.is_reversed = True
        self.reversal_entry = reversal
        self.save(update_fields=["is_reversed", "reversal_entry", "updated_at"])

        return reversal


class FinancialAccount(AuditedModel):
    """Conta financeira — saldo sempre calculado via ledger."""

    class AccountType(models.TextChoices):
        DRIVER = "driver", _("Motorista")
        SUPPLIER = "supplier", _("Fornecedor")
        OPERATIONAL = "operational", _("Operacional")
        ADVANCE_POOL = "advance_pool", _("Pool Adiantamentos")

    name = models.CharField(max_length=200, verbose_name=_("Nome"))
    account_type = models.CharField(
        max_length=20,
        choices=AccountType.choices,
        verbose_name=_("Tipo"),
        db_index=True,
    )
    linked_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    linked_id = models.UUIDField(null=True, blank=True)
    linked_object = GenericForeignKey("linked_type", "linked_id")

    class Meta(AuditedModel.Meta):
        verbose_name = _("Conta Financeira")
        verbose_name_plural = _("Contas Financeiras")
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.get_account_type_display()})"

    def get_balance(self, until_date=None) -> Decimal:
        """Saldo = soma créditos − soma débitos.

        Nota: is_reversed é metadado de display — não filtramos por ele aqui.
        O par (entry original + reversal entry) se cancela algebricamente:
        DEBIT -500 + REVERSAL CREDIT +500 = 0.
        Filtrar is_reversed=False remove o débito mas mantém o crédito → saldo errado.
        """
        qs = self.entries.filter(is_active=True)
        if until_date:
            qs = qs.filter(competence_date__lte=until_date)

        result = qs.aggregate(
            total_credits=Sum(
                "amount",
                filter=models.Q(direction=LedgerEntry.Direction.CREDIT),
                default=Decimal("0"),
            ),
            total_debits=Sum(
                "amount",
                filter=models.Q(direction=LedgerEntry.Direction.DEBIT),
                default=Decimal("0"),
            ),
        )
        return result["total_credits"] - result["total_debits"]

    @property
    def current_balance(self) -> Decimal:
        return self.get_balance()
