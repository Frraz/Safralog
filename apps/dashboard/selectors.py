"""
SafraLog — apps/dashboard/selectors.py
Query layer for the dashboard.

get_dashboard_stats(tenant) → full context dict for DashboardView

Every key, every sub-key, every object attribute returned here matches
exactly what templates/dashboard/index.html expects.  No mismatches.

Design notes
------------
* faturamento_bruto is computed from Waybill data, NOT from LedgerEntry,
  because the seed script sets status=CONFIRMED directly without going
  through WaybillConfirmView, so production LedgerEntry credits are absent.
* debits (fuel + advance) DO exist in LedgerEntry so those come from there.
* All "romaneio" proxy objects expose Portuguese attribute names to match
  the template (motorista, talhao, veiculo, status em português, etc.).
* SimpleNamespace is used so Django templates can do obj.attr lookups.
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace

from django.db.models import Count, DecimalField, ExpressionWrapper, F, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

# ── Constants ─────────────────────────────────────────────────────────────────

_ZERO = Decimal("0")
_CONFIRMED_STATUSES = ("confirmed", "settled")

# ── Lazy model imports (avoid circular imports at module load) ────────────────


def _Waybill():
    from apps.operations.models import Waybill

    return Waybill


def _Harvest():
    from apps.operations.models import Harvest

    return Harvest


def _Driver():
    from apps.logistics.models import Driver

    return Driver


def _Vehicle():
    from apps.logistics.models import Vehicle

    return Vehicle


def _Fueling():
    from apps.logistics.models import Fueling

    return Fueling


def _LedgerEntry():
    from apps.finance.models import LedgerEntry

    return LedgerEntry


def _Settlement():
    from apps.finance.models import Settlement

    return Settlement


def _Advance():
    from apps.finance.models import Advance

    return Advance


def _FinancialAccount():
    from apps.finance.models import FinancialAccount

    return FinancialAccount


# ── Helpers ───────────────────────────────────────────────────────────────────


def _today() -> date:
    return timezone.localdate()


def _to_tons(kg) -> Decimal:
    if kg is None:
        return _ZERO
    return Decimal(str(kg)) / Decimal("1000")


def _safe_pct(part, total) -> float:
    try:
        if not total or float(total) == 0:
            return 0.0
        return min(100.0, round(float(part) / float(total) * 100, 1))
    except (TypeError, ZeroDivisionError):
        return 0.0


def _initials(name: str) -> str:
    parts = name.strip().split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[-1][0]).upper()
    return name[:2].upper() if name else "??"


def _short_name(name: str) -> str:
    parts = name.strip().split()
    if len(parts) >= 2:
        return f"{parts[0]} {parts[-1]}"
    return name


def _status_pt(status: str) -> str:
    """Maps English model status to Portuguese for template comparison."""
    return {
        "confirmed": "confirmado",
        "draft": "rascunho",
        "settled": "fechado",
        "cancelled": "cancelado",
        "pending": "pendente",
        "approved": "aprovado",
        "closed": "fechado",
    }.get(status, status)


def _time_ago(dt) -> str:
    """Returns human-readable Portuguese time-ago string."""
    now = timezone.now()
    if hasattr(dt, "date"):
        diff = now - dt
    else:
        diff = timedelta(days=(now.date() - dt).days)
    seconds = int(abs(diff.total_seconds()))
    if seconds < 60:
        return "agora"
    if seconds < 3600:
        m = seconds // 60
        return f"há {m} min"
    if seconds < 86400:
        h = seconds // 3600
        return f"há {h}h"
    d = seconds // 86400
    return f"há {d}d" if d < 30 else dt.strftime("%d/%m") if hasattr(dt, "strftime") else "—"


def _waybill_value_expr():
    """DB expression: (gross_weight - tare_weight) / 1000 * unit_price"""
    return ExpressionWrapper(
        (F("gross_weight") - F("tare_weight")) * F("unit_price") / Decimal("1000"),
        output_field=DecimalField(max_digits=18, decimal_places=4),
    )


# ── Internal data builders ────────────────────────────────────────────────────


def _get_active_harvest(tenant):
    return _Harvest().objects.filter(tenant=tenant, status="active").order_by("-start_date").first()


def _get_daily_chart_data(tenant) -> list[dict]:
    """
    Returns last 30 days of confirmed+settled tonnage.
    Gaps (days with no waybills) are filled with zeros.
    """
    today = _today()
    start = today - timedelta(days=29)
    Waybill = _Waybill()

    rows = (
        Waybill.objects.filter(
            tenant=tenant,
            status__in=_CONFIRMED_STATUSES,
            operation_date__gte=start,
            operation_date__lte=today,
        )
        .values("operation_date")
        .annotate(
            gross=Coalesce(Sum("gross_weight"), _ZERO),
            tare=Coalesce(Sum("tare_weight"), _ZERO),
            count=Count("id"),
        )
        .order_by("operation_date")
    )

    by_date = {r["operation_date"]: r for r in rows}

    result = []
    for i in range(30):
        d = start + timedelta(days=i)
        row = by_date.get(d)
        if row:
            tons = float(_to_tons(row["gross"] - row["tare"]))
            count = row["count"]
        else:
            tons = 0.0
            count = 0
        result.append(
            {
                "data": d.strftime("%d/%m"),
                "date": d,
                "tonelagem": tons,
                "tons": tons,
                "count": count,
            }
        )
    return result


def _get_kpi_stats(tenant, active_harvest, daily_chart_data: list[dict]) -> dict:
    """
    Computes every KPI value the dashboard template needs under the
    `stats` context key.
    """
    today = _today()
    Waybill = _Waybill()
    Fueling = _Fueling()
    LedgerEntry = _LedgerEntry()
    Settlement = _Settlement()
    Vehicle = _Vehicle()
    Driver = _Driver()

    # ── Today ─────────────────────────────────────────────────────────────
    today_agg = Waybill.objects.filter(
        tenant=tenant,
        status__in=_CONFIRMED_STATUSES,
        operation_date=today,
    ).aggregate(
        gross=Coalesce(Sum("gross_weight"), _ZERO),
        tare=Coalesce(Sum("tare_weight"), _ZERO),
        count=Count("id"),
    )
    hoje_tonelagem = float(_to_tons(today_agg["gross"] - today_agg["tare"]))
    hoje_romaneios = today_agg["count"]

    yesterday = today - timedelta(days=1)
    yesterday_agg = Waybill.objects.filter(
        tenant=tenant,
        status__in=_CONFIRMED_STATUSES,
        operation_date=yesterday,
    ).aggregate(
        gross=Coalesce(Sum("gross_weight"), _ZERO),
        tare=Coalesce(Sum("tare_weight"), _ZERO),
    )
    yesterday_tons = float(_to_tons(yesterday_agg["gross"] - yesterday_agg["tare"]))
    if yesterday_tons > 0:
        hoje_variacao = round((hoje_tonelagem - yesterday_tons) / yesterday_tons * 100, 1)
    else:
        hoje_variacao = 0.0

    # ── This week ─────────────────────────────────────────────────────────
    week_start = today - timedelta(days=today.weekday())
    week_agg = Waybill.objects.filter(
        tenant=tenant,
        status__in=_CONFIRMED_STATUSES,
        operation_date__gte=week_start,
        operation_date__lte=today,
    ).aggregate(
        gross=Coalesce(Sum("gross_weight"), _ZERO),
        tare=Coalesce(Sum("tare_weight"), _ZERO),
        count=Count("id"),
    )
    semana_tonelagem = float(_to_tons(week_agg["gross"] - week_agg["tare"]))
    semana_romaneios = week_agg["count"]

    # ── Harvest totals ─────────────────────────────────────────────────────
    harvest_filter = {"harvest": active_harvest} if active_harvest else {}
    harvest_agg = Waybill.objects.filter(
        tenant=tenant,
        status__in=_CONFIRMED_STATUSES,
        **harvest_filter,
    ).aggregate(
        gross=Coalesce(Sum("gross_weight"), _ZERO),
        tare=Coalesce(Sum("tare_weight"), _ZERO),
        count=Count("id"),
    )
    total_tonelagem = float(_to_tons(harvest_agg["gross"] - harvest_agg["tare"]))
    total_romaneios = harvest_agg["count"]

    # ── Active drivers today ───────────────────────────────────────────────
    motoristas_ativos = (
        Waybill.objects.filter(
            tenant=tenant,
            operation_date=today,
            is_active=True,
        )
        .values("driver_id")
        .distinct()
        .count()
    )

    # ── Fuel this month ────────────────────────────────────────────────────
    month_start = today.replace(day=1)
    fuel_records = list(
        Fueling.objects.filter(
            tenant=tenant,
            fueling_date__gte=month_start,
            fueling_date__lte=today,
            is_active=True,
        )
    )
    combustivel_litros = sum(float(f.liters) for f in fuel_records)
    combustivel_valor = sum(float(f.driver_debit_total) for f in fuel_records)

    # ── Pending settlements ────────────────────────────────────────────────
    pending_qs = Settlement.objects.filter(
        tenant=tenant,
        status="pending",
        is_active=True,
    )
    fechamentos_pendentes = pending_qs.count()
    a_pagar_agg = pending_qs.aggregate(total=Coalesce(Sum("snapshot_net_balance"), _ZERO))
    a_pagar = float(a_pagar_agg["total"])

    # ── Financial: faturamento (from Waybill data, not LedgerEntry) ────────
    # Seed bypasses WaybillConfirmView so LedgerEntry credits may be absent.
    # Use the waybill data directly for reliability.
    fat_agg = Waybill.objects.filter(
        tenant=tenant,
        status__in=_CONFIRMED_STATUSES,
        operation_date__gte=month_start,
        operation_date__lte=today,
    ).aggregate(total=Coalesce(Sum(_waybill_value_expr()), _ZERO))
    faturamento_bruto = float(fat_agg["total"])

    # Previous month for variation
    if month_start.month == 1:
        prev_start = month_start.replace(year=month_start.year - 1, month=12)
    else:
        prev_start = month_start.replace(month=month_start.month - 1)
    prev_end = month_start - timedelta(days=1)
    prev_agg = Waybill.objects.filter(
        tenant=tenant,
        status__in=_CONFIRMED_STATUSES,
        operation_date__gte=prev_start,
        operation_date__lte=prev_end,
    ).aggregate(total=Coalesce(Sum(_waybill_value_expr()), _ZERO))
    prev_fat = float(prev_agg["total"])
    if prev_fat > 0:
        faturamento_variacao = round((faturamento_bruto - prev_fat) / prev_fat * 100, 1)
    else:
        faturamento_variacao = 0.0

    # ── Debits this month (from LedgerEntry — always correct) ──────────────
    debits_agg = LedgerEntry.objects.filter(
        tenant=tenant,
        direction="debit",
        competence_date__gte=month_start,
        competence_date__lte=today,
        is_reversed=False,
        is_active=True,
    ).aggregate(total=Coalesce(Sum("amount"), _ZERO))
    total_debitos = float(debits_agg["total"])

    # ── Cost per ton (fuel cost / total_tonelagem) ──────────────────────────
    if total_tonelagem > 0:
        custo_por_tonelada = round(combustivel_valor / total_tonelagem, 2)
    else:
        custo_por_tonelada = 0.0

    # ── Driver balances ────────────────────────────────────────────────────
    FinancialAccount = _FinancialAccount()
    accounts = list(
        FinancialAccount.objects.filter(
            tenant=tenant,
            account_type="driver",
            is_active=True,
        )
    )
    balances = [acc.current_balance for acc in accounts]
    saldo_total_motoristas = float(sum(balances))
    motoristas_positivos = sum(1 for b in balances if b >= 0)

    # ── Chart KPIs ─────────────────────────────────────────────────────────
    active_days = sum(1 for d in daily_chart_data if d["count"] > 0)
    total_tons_30d = sum(d["tons"] for d in daily_chart_data)
    pico_tonelagem = max((d["tons"] for d in daily_chart_data), default=0.0)
    media_diaria = round(total_tons_30d / active_days, 1) if active_days else 0.0

    # ── Waybill status summary (harvest scope) ─────────────────────────────
    base_qs = Waybill.objects.filter(tenant=tenant, is_active=True, **harvest_filter)

    def _status_agg(status):
        return base_qs.filter(status=status).aggregate(
            count=Count("id"),
            gross=Coalesce(Sum("gross_weight"), _ZERO),
            tare=Coalesce(Sum("tare_weight"), _ZERO),
        )

    confirmed_agg = _status_agg("confirmed")
    draft_agg = _status_agg("draft")
    settled_agg = _status_agg("settled")

    total_count = (confirmed_agg["count"] + draft_agg["count"] + settled_agg["count"]) or 1

    rom_confirmados = confirmed_agg["count"]
    rom_confirmados_t = float(_to_tons(confirmed_agg["gross"] - confirmed_agg["tare"]))
    rom_confirmados_pct = _safe_pct(rom_confirmados, total_count)

    rom_rascunhos = draft_agg["count"]
    rom_rascunhos_t = float(_to_tons(draft_agg["gross"] - draft_agg["tare"]))
    rom_rascunhos_pct = _safe_pct(rom_rascunhos, total_count)

    rom_fechados = settled_agg["count"]
    rom_fechados_t = float(_to_tons(settled_agg["gross"] - settled_agg["tare"]))
    rom_fechados_pct = _safe_pct(rom_fechados, total_count)

    # ── Fleet ──────────────────────────────────────────────────────────────
    veiculos_total = Vehicle.objects.filter(tenant=tenant).count()
    veiculos_ativos = Vehicle.objects.filter(tenant=tenant, is_active=True, status="active").count()
    carga_media_viagem = round(total_tonelagem / total_romaneios, 2) if total_romaneios else 0.0

    return {
        # Operational
        "hoje_tonelagem": hoje_tonelagem,
        "hoje_romaneios": hoje_romaneios,
        "hoje_variacao": hoje_variacao,
        "semana_tonelagem": semana_tonelagem,
        "semana_romaneios": semana_romaneios,
        "total_tonelagem": total_tonelagem,
        "total_romaneios": total_romaneios,
        "motoristas_ativos": motoristas_ativos,
        "combustivel_litros": combustivel_litros,
        "combustivel_valor": combustivel_valor,
        "a_pagar": a_pagar,
        "fechamentos_pendentes": fechamentos_pendentes,
        # Financial
        "faturamento_bruto": faturamento_bruto,
        "faturamento_variacao": faturamento_variacao,
        "custo_por_tonelada": custo_por_tonelada,
        "saldo_total_motoristas": saldo_total_motoristas,
        "motoristas_positivos": motoristas_positivos,
        "total_debitos": total_debitos,
        # Chart
        "pico_tonelagem": pico_tonelagem,
        "media_diaria": media_diaria,
        "dias_ativos": active_days,
        # Waybill status bars
        "rom_confirmados": rom_confirmados,
        "rom_confirmados_t": rom_confirmados_t,
        "rom_confirmados_pct": rom_confirmados_pct,
        "rom_rascunhos": rom_rascunhos,
        "rom_rascunhos_t": rom_rascunhos_t,
        "rom_rascunhos_pct": rom_rascunhos_pct,
        "rom_fechados": rom_fechados,
        "rom_fechados_t": rom_fechados_t,
        "rom_fechados_pct": rom_fechados_pct,
        "romaneios_rascunho": rom_rascunhos,
        # Fleet
        "veiculos_ativos": veiculos_ativos,
        "veiculos_total": veiculos_total,
        "carga_media_viagem": carga_media_viagem,
    }


# ── Proxy builders ────────────────────────────────────────────────────────────


def _build_safra_proxy(harvest, total_tonelagem: float):
    """Returns a SimpleNamespace with the attrs the template expects."""
    if not harvest:
        return None
    percentual = 0
    if getattr(harvest, "expected_area_ha", None) and getattr(
        harvest, "expected_yield_ton_ha", None
    ):
        target = float(harvest.expected_area_ha) * float(harvest.expected_yield_ton_ha)
        if target > 0:
            percentual = min(100, round(total_tonelagem / target * 100, 1))
    return SimpleNamespace(
        pk=harvest.pk,
        nome=harvest.name,
        percentual_completo=percentual,
        data_inicio=harvest.start_date,
    )


def _recent_waybill_proxies(tenant, limit: int = 12) -> list:
    """
    Returns the most recent waybills as proxy objects that match the
    template's `romaneios_recentes` loop:

        rom.pk, rom.numero, rom.motorista.iniciais, rom.motorista.nome_curto,
        rom.talhao.nome, rom.veiculo.placa, rom.status (PT), rom.peso_liquido (t),
        rom.data
    """
    Waybill = _Waybill()
    waybills = (
        Waybill.objects.filter(tenant=tenant, is_active=True)
        .select_related("driver", "vehicle", "field")
        .order_by("-operation_date", "-number")[:limit]
    )

    result = []
    for w in waybills:
        driver_name = w.driver.name if w.driver else "—"
        result.append(
            SimpleNamespace(
                pk=w.pk,
                numero=w.number,
                motorista=SimpleNamespace(
                    iniciais=_initials(driver_name),
                    nome_curto=_short_name(driver_name),
                ),
                talhao=SimpleNamespace(nome=w.field.name if w.field else "—"),
                veiculo=SimpleNamespace(placa=w.vehicle.plate if w.vehicle else "—"),
                status=_status_pt(w.status),
                peso_liquido=float(_to_tons(w.gross_weight - w.tare_weight)),
                data=w.operation_date,
            )
        )
    return result


def _driver_ranking_proxies(tenant, month: date | None = None, limit: int = 7) -> list:
    """
    Returns top drivers by tonnage for the given month.
    Template loop: pos.motorista.nome_curto, pos.total_tonelagem, pos.percentual
    """
    Waybill = _Waybill()
    today = _today()
    if month is None:
        month = today
    month_start = month.replace(day=1)
    if month_start.month == 12:
        month_end = month_start.replace(year=month_start.year + 1, month=1) - timedelta(days=1)
    else:
        month_end = month_start.replace(month=month_start.month + 1) - timedelta(days=1)

    rows = list(
        Waybill.objects.filter(
            tenant=tenant,
            status__in=_CONFIRMED_STATUSES,
            operation_date__gte=month_start,
            operation_date__lte=month_end,
            driver__isnull=False,
        )
        .values("driver__id", "driver__name")
        .annotate(
            gross=Coalesce(Sum("gross_weight"), _ZERO),
            tare=Coalesce(Sum("tare_weight"), _ZERO),
        )
        .order_by("-gross")[:limit]
    )

    if not rows:
        return []

    max_kg = float(rows[0]["gross"] - rows[0]["tare"]) or 1

    result = []
    for row in rows:
        net_kg = float(row["gross"] - row["tare"])
        name = row["driver__name"] or "—"
        result.append(
            SimpleNamespace(
                motorista=SimpleNamespace(
                    nome_curto=_short_name(name),
                    iniciais=_initials(name),
                ),
                total_tonelagem=float(_to_tons(net_kg)),
                percentual=_safe_pct(net_kg, max_kg),
            )
        )
    return result


def _vehicle_ranking_proxies(tenant, limit: int = 5) -> list:
    """
    Returns top vehicles by tonnage this month.
    Template loop: vei.veiculo.placa, vei.total_tonelagem, vei.percentual
    """
    Waybill = _Waybill()
    today = _today()
    month_start = today.replace(day=1)

    rows = list(
        Waybill.objects.filter(
            tenant=tenant,
            status__in=_CONFIRMED_STATUSES,
            operation_date__gte=month_start,
            vehicle__isnull=False,
        )
        .values("vehicle__id", "vehicle__plate")
        .annotate(
            gross=Coalesce(Sum("gross_weight"), _ZERO),
            tare=Coalesce(Sum("tare_weight"), _ZERO),
        )
        .order_by("-gross")[:limit]
    )

    if not rows:
        return []

    max_kg = float(rows[0]["gross"] - rows[0]["tare"]) or 1

    result = []
    for row in rows:
        net_kg = float(row["gross"] - row["tare"])
        result.append(
            SimpleNamespace(
                veiculo=SimpleNamespace(placa=row["vehicle__plate"] or "—"),
                total_tonelagem=float(_to_tons(net_kg)),
                percentual=_safe_pct(net_kg, max_kg),
            )
        )
    return result


def _driver_balances_proxies(tenant, limit: int = 6) -> list:
    """
    Returns driver balances sorted by balance desc.
    Template loop: mot.motorista.pk, mot.motorista.iniciais,
                   mot.motorista.nome_curto, mot.saldo
    """
    Driver = _Driver()
    drivers = (
        Driver.objects.filter(tenant=tenant, is_active=True)
        .select_related("financial_account")
        .order_by("name")
    )

    result = []
    for driver in drivers:
        acc = driver.financial_account
        bal = float(acc.current_balance) if acc else 0.0
        result.append(
            SimpleNamespace(
                motorista=SimpleNamespace(
                    pk=driver.pk,
                    iniciais=_initials(driver.name),
                    nome_curto=_short_name(driver.name),
                ),
                saldo=bal,
            )
        )

    result.sort(key=lambda x: x.saldo, reverse=True)
    return result[:limit]


def _motoristas_negativos_proxies(tenant) -> list:
    """Returns drivers with negative account balance."""
    Driver = _Driver()
    drivers = Driver.objects.filter(tenant=tenant, is_active=True).select_related(
        "financial_account"
    )
    result = []
    for driver in drivers:
        acc = driver.financial_account
        if acc and acc.current_balance < 0:
            result.append(
                SimpleNamespace(
                    nome=driver.name,
                    saldo=float(acc.current_balance),
                )
            )
    return result


def _activity_feed_proxies(tenant, limit: int = 20) -> list:
    """
    Merges recent waybills, fuelings, advances, settlements into a
    unified activity timeline.
    Template: log.tipo, log.descricao, log.quando, log.usuario
    """
    Waybill = _Waybill()
    Fueling = _Fueling()
    Advance = _Advance()
    Settlement = _Settlement()

    items = []

    for w in (
        Waybill.objects.filter(tenant=tenant).select_related("driver").order_by("-created_at")[:10]
    ):
        driver_name = w.driver.name if w.driver else "—"
        net_t = float(_to_tons(w.gross_weight - w.tare_weight))
        items.append(
            {
                "tipo": "romaneio",
                "descricao": f"Romaneio #{w.number} — {_short_name(driver_name)} · {net_t:.1f} t",
                "dt": w.created_at,
                "usuario": _short_name(driver_name),
            }
        )

    for f in (
        Fueling.objects.filter(tenant=tenant).select_related("driver").order_by("-created_at")[:5]
    ):
        driver_name = f.driver.name if f.driver else "—"
        cost = float(f.driver_debit_total)
        items.append(
            {
                "tipo": "abastecimento",
                "descricao": (
                    f"Abastecimento — {_short_name(driver_name)}"
                    f" · {float(f.liters):.0f} L / R$ {cost:.2f}"
                ),
                "dt": f.created_at,
                "usuario": _short_name(driver_name),
            }
        )

    for a in (
        Advance.objects.filter(tenant=tenant).select_related("driver").order_by("-created_at")[:5]
    ):
        driver_name = a.driver.name if a.driver else "—"
        items.append(
            {
                "tipo": "adiantamento",
                "descricao": (
                    f"Adiantamento — {_short_name(driver_name)} · R$ {float(a.amount):.2f}"
                ),
                "dt": a.created_at,
                "usuario": _short_name(driver_name),
            }
        )

    for s in (
        Settlement.objects.filter(tenant=tenant)
        .select_related("account")
        .order_by("-created_at")[:5]
    ):
        acc_name = (s.account.name or "—") if s.account else "—"
        driver_name = acc_name.replace("Conta — ", "")
        net = float(s.snapshot_net_balance or 0)
        items.append(
            {
                "tipo": "fechamento",
                "descricao": f"Fechamento — {driver_name} · R$ {net:.2f}",
                "dt": s.created_at,
                "usuario": "Sistema",
            }
        )

    items.sort(key=lambda x: x["dt"], reverse=True)

    return [
        SimpleNamespace(
            tipo=item["tipo"],
            descricao=item["descricao"],
            quando=_time_ago(item["dt"]),
            usuario=item["usuario"],
        )
        for item in items[:limit]
    ]


def _build_insights(tenant, stats: dict, daily_chart_data: list[dict]) -> SimpleNamespace:
    """
    Builds the `insights` SimpleNamespace the template reads with:
        insights.motoristas_inativos / .motoristas_inativos_nomes
        insights.pico_dia / .pico_dia_texto
        insights.custo_alto / .custo_alto_texto
    """
    today = _today()
    Driver = _Driver()
    Waybill = _Waybill()

    # --- Inactive drivers (no waybill in 3+ days) -------------------------
    cutoff = today - timedelta(days=3)
    active_driver_ids = (
        Waybill.objects.filter(
            tenant=tenant,
            operation_date__gte=cutoff,
            is_active=True,
        )
        .values_list("driver_id", flat=True)
        .distinct()
    )
    inactive_qs = Driver.objects.filter(
        tenant=tenant,
        is_active=True,
        status="active",
    ).exclude(id__in=active_driver_ids)

    motoristas_inativos = inactive_qs.exists()
    motoristas_inativos_nomes = ""
    if motoristas_inativos:
        names = [_short_name(d.name) for d in inactive_qs[:3]]
        motoristas_inativos_nomes = ", ".join(names)

    # --- Peak day ──────────────────────────────────────────────────────────
    pico_dia = False
    pico_dia_texto = ""
    if daily_chart_data:
        peak = max(daily_chart_data, key=lambda d: d["tons"])
        if peak["tons"] > 0:
            pico_dia = True
            pico_dia_texto = f"Maior produção: {peak['tons']:.1f} t em {peak['data']}"

    # --- High cost per ton ─────────────────────────────────────────────────
    custo_alto = False
    custo_alto_texto = ""
    cpt = stats.get("custo_por_tonelada", 0)
    fat = stats.get("faturamento_bruto", 0)
    tons = stats.get("total_tonelagem", 0)
    if cpt > 0 and fat > 0 and tons > 0:
        rev_per_ton = fat / tons
        if rev_per_ton > 0 and cpt > rev_per_ton * 0.20:
            pct = round(cpt / rev_per_ton * 100, 0)
            custo_alto = True
            custo_alto_texto = f"Custo/t R$ {cpt:.2f} representa {pct:.0f}% da receita por tonelada"

    return SimpleNamespace(
        motoristas_inativos=motoristas_inativos,
        motoristas_inativos_nomes=motoristas_inativos_nomes,
        pico_dia=pico_dia,
        pico_dia_texto=pico_dia_texto,
        custo_alto=custo_alto,
        custo_alto_texto=custo_alto_texto,
    )


# ── Public API ────────────────────────────────────────────────────────────────


def get_dashboard_stats(tenant) -> dict:
    """
    Returns the complete context dict for DashboardView.
    Every key matches exactly what templates/dashboard/index.html expects.
    """
    active_harvest = _get_active_harvest(tenant)
    daily_chart_data = _get_daily_chart_data(tenant)

    stats = _get_kpi_stats(tenant, active_harvest, daily_chart_data)

    safra_ativa = _build_safra_proxy(active_harvest, stats["total_tonelagem"])

    chart_tonelagem_json = json.dumps(
        [{"data": d["data"], "tonelagem": d["tonelagem"]} for d in daily_chart_data]
    )

    return {
        # Harvest banner
        "safra_ativa": safra_ativa,
        # Negative-balance alert
        "motoristas_negativos": _motoristas_negativos_proxies(tenant),
        # All KPI numbers (flat dict — template accesses as stats.xxx)
        "stats": stats,
        # Chart JSON string
        "chart_tonelagem_json": chart_tonelagem_json,
        # Waybill table
        "romaneios_recentes": _recent_waybill_proxies(tenant),
        # Driver ranking sidebar
        "ranking_motoristas": _driver_ranking_proxies(tenant),
        # Vehicle ranking
        "top_veiculos": _vehicle_ranking_proxies(tenant),
        # Financial sidebar
        "saldos_motoristas": _driver_balances_proxies(tenant),
        # Activity timeline
        "atividade_recente": _activity_feed_proxies(tenant),
        # Insight cards
        "insights": _build_insights(tenant, stats, daily_chart_data),
    }


# ── Secondary public helpers (used by other views) ────────────────────────────


def get_harvest_stats(tenant, harvest=None) -> dict:
    if harvest is None:
        harvest = _get_active_harvest(tenant)
    if not harvest:
        return {"harvest_total_tons": 0.0, "harvest_waybill_count": 0, "harvest": None}

    agg = (
        _Waybill()
        .objects.filter(
            tenant=tenant,
            harvest=harvest,
            status__in=_CONFIRMED_STATUSES,
        )
        .aggregate(
            gross=Coalesce(Sum("gross_weight"), _ZERO),
            tare=Coalesce(Sum("tare_weight"), _ZERO),
            count=Count("id"),
        )
    )
    return {
        "harvest_total_tons": float(_to_tons(agg["gross"] - agg["tare"])),
        "harvest_waybill_count": agg["count"],
        "harvest": harvest,
    }


def get_recent_waybills(tenant, limit: int = 10):
    return _recent_waybill_proxies(tenant, limit=limit)


def get_driver_ranking(tenant, month: date | None = None, limit: int = 10) -> list:
    return _driver_ranking_proxies(tenant, month=month, limit=limit)


def get_field_stats(tenant, harvest=None) -> list:
    Waybill = _Waybill()
    if harvest is None:
        harvest = _get_active_harvest(tenant)
    qs = Waybill.objects.filter(tenant=tenant, status__in=_CONFIRMED_STATUSES)
    if harvest:
        qs = qs.filter(harvest=harvest)
    rows = (
        qs.values("field__id", "field__name")
        .annotate(
            gross=Coalesce(Sum("gross_weight"), _ZERO),
            tare=Coalesce(Sum("tare_weight"), _ZERO),
            count=Count("id"),
        )
        .order_by("-gross")
    )
    return [
        {
            "field_name": r["field__name"],
            "total_tons": float(_to_tons(r["gross"] - r["tare"])),
            "waybill_count": r["count"],
        }
        for r in rows
    ]
