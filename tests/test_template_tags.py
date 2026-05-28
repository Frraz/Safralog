"""
SafraLog — tests/test_template_tags.py
Testa os filters e tags de apps/core/templatetags/core_tags.py.
"""

from __future__ import annotations

from decimal import Decimal

from apps.core.templatetags.core_tags import (
    absolute,
    currency_br,
    floatformat_br,
    initials,
    kg_to_tons,
    percentage,
)

# ── currency_br ───────────────────────────────────────────────────────────────


class TestCurrencyBr:
    def test_valor_simples(self):
        assert currency_br(Decimal("1234.56")) == "R$ 1.234,56"

    def test_valor_inteiro(self):
        assert currency_br(Decimal("1000")) == "R$ 1.000,00"

    def test_valor_pequeno(self):
        assert currency_br(Decimal("0.50")) == "R$ 0,50"

    def test_zero(self):
        assert currency_br(Decimal("0")) == "R$ 0,00"

    def test_none(self):
        assert currency_br(None) == "R$ 0,00"

    def test_negativo(self):
        assert currency_br(Decimal("-500.00")) == "-R$ 500,00"

    def test_milhar(self):
        assert currency_br(Decimal("1000000.00")) == "R$ 1.000.000,00"

    def test_arredondamento(self):
        # 1234.999 deve arredondar para 1235.00
        assert currency_br(Decimal("1234.999")) == "R$ 1.235,00"

    def test_string_numerica(self):
        assert currency_br("250.75") == "R$ 250,75"

    def test_float(self):
        assert currency_br(100.0) == "R$ 100,00"

    def test_valor_invalido(self):
        assert currency_br("abc") == "R$ 0,00"

    def test_valor_grande(self):
        assert currency_br(Decimal("9999999.99")) == "R$ 9.999.999,99"


# ── kg_to_tons ────────────────────────────────────────────────────────────────


class TestKgToTons:
    def test_valor_simples(self):
        assert kg_to_tons(Decimal("50000")) == "50,000 t"

    def test_zero(self):
        assert kg_to_tons(Decimal("0")) == "0,000 t"

    def test_none(self):
        assert kg_to_tons(None) == "0,000 t"

    def test_arredondamento_tres_casas(self):
        # 36000 kg = 36.000 t
        assert kg_to_tons(Decimal("36000")) == "36,000 t"

    def test_valor_fracionado(self):
        # 1500.5 kg = 1.501 t (arredonda ROUND_HALF_UP)
        result = kg_to_tons(Decimal("1500.5"))
        assert result == "1,501 t"

    def test_valor_grande(self):
        assert kg_to_tons(Decimal("1000000")) == "1.000,000 t"

    def test_float(self):
        result = kg_to_tons(14000.0)
        assert result == "14,000 t"

    def test_string_numerica(self):
        assert kg_to_tons("50000") == "50,000 t"

    def test_valor_invalido(self):
        assert kg_to_tons("abc") == "0,000 t"

    def test_peso_romaneio_tipico(self):
        # Romaneio típico: bruto 50000 - tara 14000 = 36000 kg = 36 t
        liquido = Decimal("50000") - Decimal("14000")
        assert kg_to_tons(liquido) == "36,000 t"


# ── floatformat_br ────────────────────────────────────────────────────────────


class TestFloatformatBr:
    def test_duas_casas_default(self):
        assert floatformat_br(Decimal("1234.56")) == "1.234,56"

    def test_tres_casas(self):
        assert floatformat_br(Decimal("1234.567"), 3) == "1.234,567"

    def test_zero_casas(self):
        assert floatformat_br(Decimal("1234.7"), 0) == "1.235"

    def test_zero(self):
        assert floatformat_br(Decimal("0")) == "0,00"

    def test_none(self):
        assert floatformat_br(None) == "0"

    def test_negativo(self):
        assert floatformat_br(Decimal("-1234.56")) == "-1.234,56"

    def test_milhar(self):
        assert floatformat_br(Decimal("1000000.00")) == "1.000.000,00"

    def test_percentual(self):
        assert floatformat_br(Decimal("75.3"), 1) == "75,3"

    def test_string_numerica(self):
        assert floatformat_br("99.99") == "99,99"

    def test_valor_invalido(self):
        assert floatformat_br("abc") == "0"

    def test_arredondamento_half_up(self):
        # 1.005 com 2 casas → 1,01 (ROUND_HALF_UP)
        assert floatformat_br(Decimal("1.005"), 2) == "1,01"


# ── initials ──────────────────────────────────────────────────────────────────


class TestInitials:
    def test_nome_completo(self):
        assert initials("João da Silva") == "JS"

    def test_nome_simples(self):
        # Uma palavra → 2 primeiros chars
        assert initials("Maria") == "MA"

    def test_nome_vazio(self):
        assert initials("") == "?"

    def test_none_string(self):
        # None não é string, mas o filter recebe str
        assert initials("") == "?"

    def test_dois_nomes(self):
        assert initials("Ana Lima") == "AL"

    def test_nome_com_espacos_extras(self):
        assert initials("  Carlos  Santos  ") == "CS"

    def test_nome_uppercase(self):
        result = initials("pedro alves")
        assert result == result.upper()

    def test_nome_com_preposicao(self):
        # "João da Silva" → J (primeiro) + S (último)
        assert initials("João da Silva") == "JS"


# ── absolute ──────────────────────────────────────────────────────────────────


class TestAbsolute:
    def test_positivo(self):
        assert absolute(Decimal("100")) == Decimal("100")

    def test_negativo(self):
        assert absolute(Decimal("-500")) == Decimal("500")

    def test_zero(self):
        assert absolute(Decimal("0")) == Decimal("0")

    def test_float(self):
        assert absolute(-99.9) == Decimal("99.9")

    def test_invalido(self):
        assert absolute("abc") == Decimal("0")


# ── percentage ────────────────────────────────────────────────────────────────


class TestPercentage:
    def test_metade(self):
        assert percentage(Decimal("50"), Decimal("100")) == "50,0%"

    def test_tres_quartos(self):
        assert percentage(Decimal("75"), Decimal("100")) == "75,0%"

    def test_total_zero(self):
        assert percentage(Decimal("50"), Decimal("0")) == "0,0%"

    def test_total_none(self):
        assert percentage(Decimal("50"), None) == "0,0%"

    def test_valor_zero(self):
        assert percentage(Decimal("0"), Decimal("100")) == "0,0%"

    def test_acima_de_cem(self):
        # Pode acontecer em alguns KPIs
        assert percentage(Decimal("150"), Decimal("100")) == "150,0%"

    def test_arredondamento(self):
        # 1/3 = 33.333... → 33,3%
        result = percentage(Decimal("1"), Decimal("3"))
        assert result == "33,3%"

    def test_valores_inteiros(self):
        assert percentage(3, 4) == "75,0%"
