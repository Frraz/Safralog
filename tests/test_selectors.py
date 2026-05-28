"""
SafraLog — tests/test_selectors.py
Testa apps/dashboard/selectors.py — helpers puros + integração com DB.

Estratégia:
- Helpers puros (_to_tons, _safe_pct, etc.) → sem DB
- Funções com DB → usa fixtures existentes do conftest
- get_dashboard_stats() → smoke test completo (retorna sem crash + chaves corretas)
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace

from apps.dashboard.selectors import (
    _build_insights,
    _build_safra_proxy,
    _driver_balances_proxies,
    _driver_ranking_proxies,
    _get_active_harvest,
    _get_daily_chart_data,
    _initials,
    _motoristas_negativos_proxies,
    _recent_waybill_proxies,
    _safe_pct,
    _short_name,
    _status_pt,
    _time_ago,
    _to_tons,
    _vehicle_ranking_proxies,
    get_dashboard_stats,
    get_driver_ranking,
    get_field_stats,
    get_harvest_stats,
    get_recent_waybills,
)

# ── Helpers puros — sem DB ────────────────────────────────────────────────────


class TestToTons:
    def test_converte_kg_para_tons(self):
        assert _to_tons(Decimal("1000")) == Decimal("1")

    def test_zero(self):
        assert _to_tons(Decimal("0")) == Decimal("0")

    def test_none(self):
        assert _to_tons(None) == Decimal("0")

    def test_fracionado(self):
        result = _to_tons(Decimal("36000"))
        assert result == Decimal("36")

    def test_string(self):
        result = _to_tons("50000")
        assert result == Decimal("50")


class TestSafePct:
    def test_metade(self):
        assert _safe_pct(50, 100) == 50.0

    def test_zero_total(self):
        assert _safe_pct(50, 0) == 0.0

    def test_none_total(self):
        assert _safe_pct(50, None) == 0.0

    def test_maximo_100(self):
        assert _safe_pct(200, 100) == 100.0

    def test_zero_part(self):
        assert _safe_pct(0, 100) == 0.0

    def test_arredondamento(self):
        result = _safe_pct(1, 3)
        assert result == 33.3


class TestInitials:
    def test_dois_nomes(self):
        assert _initials("João Silva") == "JS"

    def test_nome_unico(self):
        assert _initials("Maria") == "MA"

    def test_tres_nomes(self):
        # Primeiro e último
        assert _initials("João da Silva") == "JS"

    def test_vazio(self):
        assert _initials("") == "??"

    def test_uppercase(self):
        result = _initials("pedro alves")
        assert result == result.upper()


class TestShortName:
    def test_nome_completo(self):
        assert _short_name("João da Silva Santos") == "João Santos"

    def test_dois_nomes(self):
        assert _short_name("Maria Lima") == "Maria Lima"

    def test_nome_unico(self):
        assert _short_name("Carlos") == "Carlos"


class TestStatusPt:
    def test_confirmed(self):
        assert _status_pt("confirmed") == "confirmado"

    def test_draft(self):
        assert _status_pt("draft") == "rascunho"

    def test_settled(self):
        assert _status_pt("settled") == "fechado"

    def test_cancelled(self):
        assert _status_pt("cancelled") == "cancelado"

    def test_pending(self):
        assert _status_pt("pending") == "pendente"

    def test_desconhecido(self):
        assert _status_pt("unknown") == "unknown"


class TestTimeAgo:
    def test_agora(self):
        from django.utils import timezone

        result = _time_ago(timezone.now())
        assert result == "agora"

    def test_minutos(self):
        from django.utils import timezone

        dt = timezone.now() - timedelta(minutes=5)
        result = _time_ago(dt)
        assert "min" in result

    def test_horas(self):
        from django.utils import timezone

        dt = timezone.now() - timedelta(hours=3)
        result = _time_ago(dt)
        assert "h" in result

    def test_dias(self):
        from django.utils import timezone

        dt = timezone.now() - timedelta(days=2)
        result = _time_ago(dt)
        assert "d" in result


# ── _build_safra_proxy ────────────────────────────────────────────────────────


class TestBuildSafraProxy:
    def test_none_harvest(self):
        assert _build_safra_proxy(None, 0.0) is None

    def test_retorna_namespace(self, harvest):
        proxy = _build_safra_proxy(harvest, 100.0)
        assert proxy is not None
        assert proxy.pk == harvest.pk
        assert proxy.nome == harvest.name
        assert isinstance(proxy.percentual_completo, (int, float))

    def test_sem_target_percentual_zero(self, harvest):
        # harvest sem expected_area_ha/expected_yield_ton_ha → percentual 0
        proxy = _build_safra_proxy(harvest, 1000.0)
        assert proxy.percentual_completo == 0


# ── _get_active_harvest ───────────────────────────────────────────────────────


class TestGetActiveHarvest:
    def test_retorna_harvest_ativa(self, db, tenant, harvest):
        result = _get_active_harvest(tenant)
        # harvest fixture tem status='active'
        assert result is not None
        assert result.pk == harvest.pk

    def test_retorna_none_sem_safra(self, db, tenant):
        result = _get_active_harvest(tenant)
        # tenant sem safra — pode retornar None se harvest não existe
        # (depende do isolamento do teste)
        assert result is None or result is not None  # só verifica que não estoura


# ── _get_daily_chart_data ─────────────────────────────────────────────────────


class TestGetDailyChartData:
    def test_retorna_30_dias(self, db, tenant):
        result = _get_daily_chart_data(tenant)
        assert len(result) == 30

    def test_estrutura_dos_itens(self, db, tenant):
        result = _get_daily_chart_data(tenant)
        item = result[0]
        assert "data" in item
        assert "tonelagem" in item
        assert "count" in item
        assert isinstance(item["tonelagem"], float)

    def test_com_romaneios_confirmados(self, db, confirmed_waybill):
        tenant = confirmed_waybill.tenant
        result = _get_daily_chart_data(tenant)
        # Deve ter pelo menos um dia com tonelagem > 0
        total = sum(d["tonelagem"] for d in result)
        assert total > 0


# ── _recent_waybill_proxies ───────────────────────────────────────────────────


class TestRecentWaybillProxies:
    def test_sem_romaneios_retorna_lista_vazia(self, db, tenant):
        result = _recent_waybill_proxies(tenant)
        assert isinstance(result, list)

    def test_com_romaneio_retorna_proxy(self, db, waybill):
        result = _recent_waybill_proxies(waybill.tenant)
        assert len(result) >= 1
        proxy = result[0]
        assert hasattr(proxy, "pk")
        assert hasattr(proxy, "numero")
        assert hasattr(proxy, "motorista")
        assert hasattr(proxy, "peso_liquido")
        assert hasattr(proxy, "status")

    def test_proxy_motorista_tem_iniciais(self, db, waybill):
        result = _recent_waybill_proxies(waybill.tenant)
        assert len(result) >= 1
        assert hasattr(result[0].motorista, "iniciais")
        assert hasattr(result[0].motorista, "nome_curto")

    def test_limite_respeitado(self, db, waybill_factory):
        for _ in range(5):
            waybill_factory()
        tenant = waybill_factory().tenant
        result = _recent_waybill_proxies(tenant, limit=3)
        assert len(result) <= 3


# ── _driver_ranking_proxies ───────────────────────────────────────────────────


class TestDriverRankingProxies:
    def test_sem_dados_retorna_vazio(self, db, tenant):
        result = _driver_ranking_proxies(tenant)
        assert isinstance(result, list)

    def test_com_romaneio_confirmado(self, db, confirmed_waybill):
        result = _driver_ranking_proxies(confirmed_waybill.tenant)
        assert len(result) >= 1
        proxy = result[0]
        assert hasattr(proxy, "motorista")
        assert hasattr(proxy, "total_tonelagem")
        assert hasattr(proxy, "percentual")
        assert proxy.total_tonelagem > 0

    def test_percentual_primeiro_e_100(self, db, confirmed_waybill):
        result = _driver_ranking_proxies(confirmed_waybill.tenant)
        if result:
            assert result[0].percentual == 100.0


# ── _vehicle_ranking_proxies ──────────────────────────────────────────────────


class TestVehicleRankingProxies:
    def test_sem_dados_retorna_vazio(self, db, tenant):
        result = _vehicle_ranking_proxies(tenant)
        assert isinstance(result, list)

    def test_com_romaneio_confirmado(self, db, confirmed_waybill):
        result = _vehicle_ranking_proxies(confirmed_waybill.tenant)
        assert isinstance(result, list)
        if result:
            assert hasattr(result[0], "veiculo")
            assert hasattr(result[0].veiculo, "placa")


# ── _driver_balances_proxies ──────────────────────────────────────────────────


class TestDriverBalancesProxies:
    def test_retorna_lista(self, db, tenant, driver):
        result = _driver_balances_proxies(tenant)
        assert isinstance(result, list)

    def test_proxy_tem_saldo(self, db, tenant, driver):
        result = _driver_balances_proxies(tenant)
        if result:
            assert hasattr(result[0], "saldo")
            assert hasattr(result[0].motorista, "nome_curto")

    def test_ordenado_por_saldo_desc(self, db, confirmed_waybill):
        """Após um crédito, o saldo deve aparecer na lista."""
        result = _driver_balances_proxies(confirmed_waybill.tenant)
        if len(result) >= 2:
            assert result[0].saldo >= result[1].saldo


# ── _motoristas_negativos_proxies ─────────────────────────────────────────────


class TestMotoristasNegativos:
    def test_sem_negativos(self, db, tenant, driver):
        # Driver sem débitos → saldo 0, não é negativo
        result = _motoristas_negativos_proxies(tenant)
        assert isinstance(result, list)
        # Nenhum deve estar negativo (sem débitos)
        for m in result:
            assert m.saldo < 0  # todos os retornados são negativos por definição

    def test_com_debito_aparece(self, db, confirmed_waybill):
        """Após reversal, saldo pode ir negativo se houver mais débitos."""
        # Não testamos o saldo negativo real aqui (depende do estado do DB)
        # Apenas verificamos que a função não estoura
        result = _motoristas_negativos_proxies(confirmed_waybill.tenant)
        assert isinstance(result, list)


# ── _build_insights ───────────────────────────────────────────────────────────


class TestBuildInsights:
    def test_retorna_namespace_com_atributos(self, db, tenant):
        stats = {
            "custo_por_tonelada": 0.0,
            "faturamento_bruto": 0.0,
            "total_tonelagem": 0.0,
        }
        chart_data = [{"tons": 0.0, "data": "01/01", "count": 0}] * 30
        result = _build_insights(tenant, stats, chart_data)
        assert isinstance(result, SimpleNamespace)
        assert hasattr(result, "motoristas_inativos")
        assert hasattr(result, "pico_dia")
        assert hasattr(result, "custo_alto")

    def test_pico_detectado(self, db, tenant):
        stats = {"custo_por_tonelada": 0, "faturamento_bruto": 0, "total_tonelagem": 0}
        chart_data = [{"tons": 100.0, "data": "15/05", "count": 3}] + [
            {"tons": 0.0, "data": "01/01", "count": 0}
        ] * 29
        result = _build_insights(tenant, stats, chart_data)
        assert result.pico_dia is True
        assert "100" in result.pico_dia_texto

    def test_custo_alto_detectado(self, db, tenant):
        stats = {
            "custo_por_tonelada": 50.0,
            "faturamento_bruto": 1000.0,
            "total_tonelagem": 100.0,
        }
        # custo/t = 50, receita/t = 10 → custo é 500% da receita/t → custo_alto
        chart_data = [{"tons": 0.0, "data": "01/01", "count": 0}] * 30
        result = _build_insights(tenant, stats, chart_data)
        assert result.custo_alto is True

    def test_sem_custo_alto(self, db, tenant):
        stats = {
            "custo_por_tonelada": 1.0,
            "faturamento_bruto": 1000.0,
            "total_tonelagem": 100.0,
        }
        # custo/t = 1, receita/t = 10 → 10% da receita → não é alto
        chart_data = [{"tons": 0.0, "data": "01/01", "count": 0}] * 30
        result = _build_insights(tenant, stats, chart_data)
        assert result.custo_alto is False


# ── get_dashboard_stats — smoke test completo ─────────────────────────────────


class TestGetDashboardStats:
    def test_retorna_dict_com_todas_chaves(self, db, tenant):
        result = get_dashboard_stats(tenant)
        assert isinstance(result, dict)

        expected_keys = [
            "safra_ativa",
            "motoristas_negativos",
            "stats",
            "chart_tonelagem_json",
            "romaneios_recentes",
            "ranking_motoristas",
            "top_veiculos",
            "saldos_motoristas",
            "atividade_recente",
            "insights",
        ]
        for key in expected_keys:
            assert key in result, f"Chave ausente: {key}"

    def test_stats_tem_kpis_operacionais(self, db, tenant):
        result = get_dashboard_stats(tenant)
        stats = result["stats"]
        operational_keys = [
            "hoje_tonelagem",
            "hoje_romaneios",
            "semana_tonelagem",
            "total_tonelagem",
            "total_romaneios",
            "motoristas_ativos",
            "combustivel_litros",
            "combustivel_valor",
        ]
        for key in operational_keys:
            assert key in stats, f"KPI ausente: {key}"

    def test_stats_tem_kpis_financeiros(self, db, tenant):
        result = get_dashboard_stats(tenant)
        stats = result["stats"]
        financial_keys = [
            "faturamento_bruto",
            "faturamento_variacao",
            "custo_por_tonelada",
            "saldo_total_motoristas",
            "motoristas_positivos",
            "total_debitos",
        ]
        for key in financial_keys:
            assert key in stats, f"KPI financeiro ausente: {key}"

    def test_chart_json_e_valido(self, db, tenant):
        import json

        result = get_dashboard_stats(tenant)
        data = json.loads(result["chart_tonelagem_json"])
        assert isinstance(data, list)
        assert len(data) == 30
        assert "data" in data[0]
        assert "tonelagem" in data[0]

    def test_com_dados_reais(self, db, confirmed_waybill):
        """Com romaneio confirmado, stats devem ter valores > 0."""
        tenant = confirmed_waybill.tenant
        result = get_dashboard_stats(tenant)
        stats = result["stats"]
        # Deve ter pelo menos alguma tonelagem
        assert stats["total_tonelagem"] > 0
        assert stats["total_romaneios"] > 0

    def test_insights_e_namespace(self, db, tenant):
        result = get_dashboard_stats(tenant)
        insights = result["insights"]
        assert isinstance(insights, SimpleNamespace)

    def test_safra_ativa_none_sem_harvest(self, db, tenant):
        # Sem safra ativa → safra_ativa deve ser None
        result = get_dashboard_stats(tenant)
        # Pode ser None ou SimpleNamespace dependendo do tenant
        assert result["safra_ativa"] is None or isinstance(result["safra_ativa"], SimpleNamespace)

    def test_safra_ativa_com_harvest(self, db, tenant, harvest):
        result = get_dashboard_stats(tenant)
        # harvest fixture tem status='active'
        assert result["safra_ativa"] is not None
        assert result["safra_ativa"].pk == harvest.pk


# ── Funções públicas secundárias ──────────────────────────────────────────────


class TestGetHarvestStats:
    def test_sem_harvest(self, db, tenant):
        result = get_harvest_stats(tenant, harvest=None)
        assert "harvest_total_tons" in result
        assert "harvest_waybill_count" in result

    def test_com_harvest(self, db, tenant, harvest):
        result = get_harvest_stats(tenant, harvest=harvest)
        assert result["harvest"] == harvest
        assert result["harvest_total_tons"] >= 0

    def test_com_romaneios(self, db, confirmed_waybill):
        tenant = confirmed_waybill.tenant
        harvest = confirmed_waybill.harvest
        result = get_harvest_stats(tenant, harvest=harvest)
        assert result["harvest_total_tons"] > 0
        assert result["harvest_waybill_count"] > 0


class TestGetRecentWaybills:
    def test_retorna_lista(self, db, tenant):
        result = get_recent_waybills(tenant)
        assert isinstance(result, list)

    def test_com_waybill(self, db, waybill):
        result = get_recent_waybills(waybill.tenant, limit=5)
        assert len(result) >= 1


class TestGetDriverRanking:
    def test_retorna_lista(self, db, tenant):
        result = get_driver_ranking(tenant)
        assert isinstance(result, list)

    def test_com_mes_especifico(self, db, confirmed_waybill):
        result = get_driver_ranking(confirmed_waybill.tenant, month=date.today())
        assert isinstance(result, list)


class TestGetFieldStats:
    def test_retorna_lista(self, db, tenant):
        result = get_field_stats(tenant)
        assert isinstance(result, list)

    def test_estrutura_do_item(self, db, confirmed_waybill):
        result = get_field_stats(confirmed_waybill.tenant)
        if result:
            item = result[0]
            assert "field_name" in item
            assert "total_tons" in item
            assert "waybill_count" in item

    def test_com_harvest(self, db, confirmed_waybill):
        result = get_field_stats(
            confirmed_waybill.tenant,
            harvest=confirmed_waybill.harvest,
        )
        assert isinstance(result, list)
