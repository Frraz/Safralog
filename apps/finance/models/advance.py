"""
SafraLog — apps/finance/models/advance.py
Adiantamento financeiro ao motorista.

Fluxo:
  PENDING → PAID (confirm()) → gera LedgerEntry de DEBIT na conta
  PENDING → CANCELLED (cancel())
  PAID → CANCELLED não é permitido (precisa de estorno via ledger)
"""

from __future__ import annotations

from decimal import Decimal

from django.db import models, transaction

from apps.core.models import AuditedModel, NoteModel


class Advance(AuditedModel, NoteModel):
    """
    Adiantamento financeiro a um motorista.

    Semântica contábil:
    - O motorista recebe dinheiro agora → DEBIT na conta (fica devendo produção)
    - No fechamento, o adiantamento é descontado do valor a pagar
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pendente"
        PAID = "paid", "Pago"
        CANCELLED = "cancelled", "Cancelado"

    class PaymentMethod(models.TextChoices):
        CASH = "cash", "Dinheiro"
        PIX = "pix", "PIX"
        BANK_TRANSFER = "bank_transfer", "Transferência"
        CHECK = "check", "Cheque"

    driver = models.ForeignKey(
        "logistics.Driver",
        on_delete=models.PROTECT,
        related_name="advances",
        verbose_name="Motorista",
    )
    harvest = models.ForeignKey(
        "operations.Harvest",
        on_delete=models.PROTECT,
        related_name="advances",
        verbose_name="Safra",
        null=True,
        blank=True,
    )
    financial_account = models.ForeignKey(
        "finance.FinancialAccount",
        on_delete=models.PROTECT,
        related_name="advances",
        verbose_name="Conta financeira",
    )

    amount = models.DecimalField(
        "Valor (R$)",
        max_digits=12,
        decimal_places=2,
    )
    payment_date = models.DateField(
        "Data do pagamento",
        db_index=True,
    )
    payment_method = models.CharField(
        "Forma de pagamento",
        max_length=20,
        choices=PaymentMethod.choices,
        default=PaymentMethod.PIX,
    )
    status = models.CharField(
        "Status",
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )

    # Preenchido ao confirmar (confirm())
    ledger_entry = models.OneToOneField(
        "finance.LedgerEntry",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="advance",
        verbose_name="Lançamento no ledger",
    )

    reference_code = models.CharField(
        "Código / comprovante",
        max_length=100,
        blank=True,
        default="",
    )

    class Meta:
        verbose_name = "Adiantamento"
        verbose_name_plural = "Adiantamentos"
        ordering = ["-payment_date", "-created_at"]
        indexes = [
            models.Index(fields=["tenant", "driver", "status"]),
            models.Index(fields=["tenant", "payment_date"]),
            models.Index(fields=["tenant", "harvest"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=Decimal("0")),
                name="advance_amount_positive",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"Adiantamento {self.driver.name} — R$ {self.amount:.2f} ({self.payment_date:%d/%m/%Y})"
        )

    # ─────────────────────────────────────────────────────────────
    # TRANSIÇÕES DE STATUS
    # ─────────────────────────────────────────────────────────────

    @transaction.atomic
    def confirm(self) -> None:
        """
        Confirma o pagamento do adiantamento.
        Gera LedgerEntry de DEBIT na conta do motorista.
        """
        if self.status != self.Status.PENDING:
            raise ValueError(
                f"Só é possível confirmar adiantamentos pendentes. "
                f"Status atual: {self.get_status_display()}"
            )

        from apps.finance.services.ledger_service import record_advance_debit

        entry = record_advance_debit(
            tenant=self.tenant,
            account=self.financial_account,
            advance=self,
        )

        self.status = self.Status.PAID
        self.ledger_entry = entry
        self.save(update_fields=["status", "ledger_entry", "updated_at"])

    @transaction.atomic
    def cancel(self, reason: str = "") -> None:
        """
        Cancela o adiantamento.
        Se já foi pago (PAID), estorna a entrada no ledger.
        """
        if self.status == self.Status.CANCELLED:
            raise ValueError("Adiantamento já cancelado.")

        if self.status == self.Status.PAID and self.ledger_entry:
            self.ledger_entry.create_reversal(
                user=None,
                reason=reason or "Cancelamento de adiantamento",
            )

        self.status = self.Status.CANCELLED
        self.save(update_fields=["status", "updated_at"])
