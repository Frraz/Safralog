"""
SafraLog — apps/finance/models/settlement.py
FECHAMENTOS — snapshots imutáveis do período financeiro.

Princípio fundamental:
- Fechamento CONGELA os dados do período.
- Após fechado, nada pode ser alterado retroativamente.
- O PDF gerado no fechamento é a versão oficial do período.
"""
from decimal import Decimal

from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import AuditedModel, NoteModel


class Settlement(AuditedModel, NoteModel):
    """
    Fechamento de período financeiro.
    Um snapshot completo e imutável dos dados do período.
    """

    class Status(models.TextChoices):
        DRAFT = "draft", _("Rascunho")
        PENDING_APPROVAL = "pending_approval", _("Aguardando aprovação")
        APPROVED = "approved", _("Aprovado")
        PAID = "paid", _("Pago")
        CLOSED = "closed", _("Fechado")
        CANCELLED = "cancelled", _("Cancelado")

    class SettlementType(models.TextChoices):
        DRIVER = "driver", _("Motorista")
        HARVEST_PERIOD = "harvest_period", _("Período de Safra")
        MONTHLY = "monthly", _("Mensal")

    # Período
    period_start = models.DateField(verbose_name=_("Início do período"))
    period_end = models.DateField(verbose_name=_("Fim do período"))

    settlement_type = models.CharField(
        max_length=20,
        choices=SettlementType.choices,
        verbose_name=_("Tipo"),
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        verbose_name=_("Status"),
        db_index=True,
    )

    # Entidade do fechamento (motorista, etc.)
    account = models.ForeignKey(
        "finance.FinancialAccount",
        on_delete=models.PROTECT,
        related_name="settlements",
        verbose_name=_("Conta"),
    )

    # =========================================================================
    # SNAPSHOT — dados congelados no momento do fechamento
    # =========================================================================
    # Estes campos são preenchidos quando status muda para CLOSED.
    # Após isso, NÃO devem ser alterados.
    snapshot_total_production = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        verbose_name=_("Snapshot: Total produção (kg)"),
    )
    snapshot_total_credits = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_("Snapshot: Total créditos (R$)"),
    )
    snapshot_total_debits = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_("Snapshot: Total débitos (R$)"),
    )
    snapshot_net_balance = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_("Snapshot: Saldo líquido (R$)"),
    )
    snapshot_waybill_count = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_("Snapshot: Qtd. romaneios"),
    )
    snapshot_data = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Snapshot: Dados completos (JSON)"),
        help_text=_(
            "JSON com todos os dados do fechamento para geração de PDF "
            "sem depender de dados vivos."
        ),
    )

    # Aprovação
    approved_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_settlements",
        verbose_name=_("Aprovado por"),
    )
    approved_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Aprovado em"),
    )
    closed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Fechado em"),
    )

    # PDF gerado
    pdf_file = models.FileField(
        upload_to="settlements/pdfs/%Y/%m/",
        blank=True,
        null=True,
        verbose_name=_("PDF do fechamento"),
    )

    # =========================================================================
    # PAGAMENTO — preenchidos quando o fechamento é marcado como pago
    # =========================================================================
    payment_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("Data do pagamento"),
    )
    payment_notes = models.TextField(
        blank=True,
        default="",
        verbose_name=_("Observações do pagamento"),
        help_text=_("PIX, número do comprovante, negociação realizada, etc."),
    )
    payment_proof = models.FileField(
        upload_to="settlements/comprovantes/%Y/%m/",
        blank=True,
        null=True,
        verbose_name=_("Comprovante de pagamento"),
        help_text=_("Foto do comprovante PIX, carta de quitação, etc."),
    )
    paid_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Marcado como pago em"),
    )
    paid_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="paid_settlements",
        verbose_name=_("Pago registrado por"),
    )

    # =========================================================================
    # OVERRIDES MANUAIS — permite editar valores antes do pagamento
    # =========================================================================
    custom_overrides = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Ajustes manuais"),
        help_text=_(
            "Sobreposições manuais de valores: romaneios com carga parcial paga "
            "como cheia, descontos negociados, créditos extras, etc."
        ),
    )


    class Meta(AuditedModel.Meta):
        verbose_name = _("Fechamento")
        verbose_name_plural = _("Fechamentos")
        ordering = ["-period_end", "-created_at"]
        indexes = [
            models.Index(fields=["account", "status"]),
            models.Index(fields=["period_start", "period_end"]),
            models.Index(fields=["status"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(period_end__gte=models.F("period_start")),
                name="settlement_period_end_gte_start",
            ),
        ]

    def __str__(self):
        return (
            f"Fechamento {self.account} | "
            f"{self.period_start} → {self.period_end} | "
            f"{self.get_status_display()}"
        )

    @property
    def is_closed(self) -> bool:
        return self.status in (self.Status.CLOSED, self.Status.PAID)

    @property
    def is_paid(self) -> bool:
        return self.status == self.Status.PAID

    @property
    def is_editable(self) -> bool:
        """Pode editar enquanto não estiver pago ou cancelado."""
        return self.status in (
            self.Status.DRAFT,
            self.Status.PENDING_APPROVAL,
            self.Status.APPROVED,
        )

    @property
    def is_open(self) -> bool:
        """Fechamento em aberto (não pago e não cancelado)."""
        return self.status not in (self.Status.PAID, self.Status.CLOSED, self.Status.CANCELLED)

    def can_be_closed(self) -> bool:
        return self.status == self.Status.APPROVED

    def can_be_paid(self) -> bool:
        """Qualquer fechamento não cancelado e não pago pode ser marcado como pago."""
        return self.status not in (self.Status.PAID, self.Status.CANCELLED, self.Status.CLOSED)

    def get_net_balance(self) -> Decimal:
        """
        Retorna saldo líquido, respeitando custom_overrides se presentes.
        Usa snapshot se fechado/pago, calcula dinamicamente se em aberto.
        """
        if self.is_closed and self.snapshot_net_balance is not None:
            return self.snapshot_net_balance
        return self.account.get_balance(until_date=self.period_end)

    def get_overridden_value(self, category: str, object_id: str, field: str, default: Decimal) -> Decimal:
        """
        Retorna o valor customizado para um item se houver override, ou o default.
        Ex: settlement.get_overridden_value('waybills', str(waybill.pk), 'custom_value', waybill.total_value)
        """
        overrides = self.custom_overrides or {}
        item_override = overrides.get(category, {}).get(str(object_id), {})
        raw = item_override.get(field)
        if raw is not None:
            try:
                return Decimal(str(raw))
            except Exception:
                pass
        return default
