"""
SafraLog — apps/logistics/models/proprietario.py
Proprietário do caminhão — pessoa que recebe o pagamento do frete.

O pagamento vai para o DONO do veículo, não necessariamente para o motorista.
Quando o motorista é o próprio dono, usar o campo `driver` para vincular.
"""
from __future__ import annotations

from django.db import models, transaction
from django.utils.translation import gettext_lazy as _

from apps.core.models import AuditedModel, NoteModel


class Proprietario(AuditedModel, NoteModel):
    """
    Dono do caminhão — favorecido no fechamento/pagamento.

    Dados bancários são necessários para emissão da ordem de pagamento.
    Se `driver` estiver preenchido, significa que o motorista e o proprietário
    são a mesma pessoa.
    """

    class BankAccountType(models.TextChoices):
        CORRENTE = "corrente", _("Conta Corrente")
        POUPANCA = "poupanca", _("Conta Poupança")
        SALARIO = "salario", _("Conta Salário")

    class PixKeyType(models.TextChoices):
        CPF = "cpf", _("CPF")
        CNPJ = "cnpj", _("CNPJ")
        EMAIL = "email", _("E-mail")
        TELEFONE = "telefone", _("Telefone")
        ALEATORIA = "aleatoria", _("Chave aleatória")

    # Dados pessoais
    name = models.CharField("Nome completo / Razão social", max_length=200)
    document = models.CharField(
        "CPF / CNPJ",
        max_length=20,
        blank=True,
        default="",
    )
    phone = models.CharField(
        "Telefone",
        max_length=20,
        blank=True,
        default="",
    )

    # Dados bancários
    bank_name = models.CharField(
        "Banco",
        max_length=100,
        blank=True,
        default="",
    )
    bank_agency = models.CharField(
        "Agência",
        max_length=20,
        blank=True,
        default="",
    )
    bank_account = models.CharField(
        "Conta",
        max_length=30,
        blank=True,
        default="",
    )
    bank_account_type = models.CharField(
        "Tipo de conta",
        max_length=20,
        choices=BankAccountType.choices,
        default=BankAccountType.CORRENTE,
        blank=True,
    )

    # PIX
    pix_key = models.CharField(
        "Chave PIX",
        max_length=150,
        blank=True,
        default="",
    )
    pix_key_type = models.CharField(
        "Tipo da chave PIX",
        max_length=20,
        choices=PixKeyType.choices,
        blank=True,
        default="",
    )

    # Vínculo: motorista é o próprio proprietário (opcional)
    driver = models.OneToOneField(
        "logistics.Driver",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="proprietario",
        verbose_name="Motorista (se for o próprio dono)",
    )

    # Conta financeira para o ledger
    financial_account = models.OneToOneField(
        "finance.FinancialAccount",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="proprietario",
        verbose_name="Conta financeira",
    )

    class Meta(AuditedModel.Meta):
        verbose_name = "Proprietário"
        verbose_name_plural = "Proprietários"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["tenant", "name"]),
        ]

    def __str__(self) -> str:
        return self.name

    @property
    def has_bank_data(self) -> bool:
        """True se ao menos banco + conta estão preenchidos."""
        return bool(self.bank_name and self.bank_account)

    @property
    def has_pix(self) -> bool:
        return bool(self.pix_key)

    @property
    def is_driver_owner(self) -> bool:
        """True quando o motorista e o proprietário são a mesma pessoa."""
        return self.driver_id is not None

    @property
    def bank_summary(self) -> str:
        """Resumo dos dados bancários para exibição."""
        parts = []
        if self.bank_name:
            parts.append(self.bank_name)
        if self.bank_agency:
            parts.append(f"Ag. {self.bank_agency}")
        if self.bank_account:
            parts.append(f"C/C {self.bank_account}")
        return " | ".join(parts) if parts else "Sem dados bancários"

    def ensure_financial_account(self) -> None:
        """
        Cria a FinancialAccount vinculada se ainda não existir.
        Chamado automaticamente no save().
        """
        if self.financial_account_id:
            return

        from apps.finance.models import FinancialAccount  # evita import circular

        account = FinancialAccount.objects.create(
            tenant=self.tenant,
            name=self.name,
            account_type=FinancialAccount.AccountType.DRIVER,
        )
        self.financial_account = account

    def save(self, *args, **kwargs):
        is_new = self._state.adding

        if is_new:
            # Garante tenant antes de chamar ensure_financial_account
            super().save(*args, **kwargs)
            with transaction.atomic():
                self.ensure_financial_account()
                Proprietario.objects.filter(pk=self.pk).update(
                    financial_account=self.financial_account
                )
        else:
            super().save(*args, **kwargs)
