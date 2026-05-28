"""
SafraLog — apps/core/templatetags/core_tags.py
Template tags e filters globais.

Uso nos templates:
  {% load core_tags %}
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from django import template
from django.urls import NoReverseMatch, reverse
from django.utils.html import format_html
from django.utils.safestring import SafeString, mark_safe

register = template.Library()


# ============================================================
# BADGE CONFIGS
# ============================================================

WAYBILL_STATUS_CONFIG: dict[str, dict] = {
    "draft": {
        "label": "Rascunho",
        "classes": "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400",
    },
    "confirmed": {
        "label": "Confirmado",
        "classes": "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
    },
    "settled": {
        "label": "Liquidado",
        "classes": "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
    },
    "cancelled": {
        "label": "Cancelado",
        "classes": "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
    },
}

DRIVER_STATUS_CONFIG: dict[str, dict] = {
    "active": {
        "label": "Ativo",
        "classes": "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
    },
    "inactive": {
        "label": "Inativo",
        "classes": "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400",
    },
    "on_leave": {
        "label": "Afastado",
        "classes": "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400",
    },
}

SETTLEMENT_STATUS_CONFIG: dict[str, dict] = {
    "draft": {
        "label": "Rascunho",
        "classes": "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400",
    },
    "pending_approval": {
        "label": "Aguardando",
        "classes": "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400",
    },
    "approved": {
        "label": "Aprovado",
        "classes": "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
    },
    "closed": {
        "label": "Fechado",
        "classes": "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
    },
    "cancelled": {
        "label": "Cancelado",
        "classes": "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
    },
}

ADVANCE_STATUS_CONFIG: dict[str, dict] = {
    "pending": {
        "label": "Pendente",
        "classes": "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400",
    },
    "paid": {
        "label": "Pago",
        "classes": "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
    },
    "cancelled": {
        "label": "Cancelado",
        "classes": "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
    },
}


# ============================================================
# SIMPLE TAGS — BADGES
# ============================================================


def _badge(config: dict, status: str) -> SafeString:
    """Renderizador genérico de badge."""
    cfg = config.get(
        status,
        {
            "label": status.replace("_", " ").title(),
            "classes": "bg-gray-100 text-gray-700",
        },
    )
    return format_html(
        '<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium {}">{}</span>',
        cfg["classes"],
        cfg["label"],
    )


@register.simple_tag
def waybill_status_badge(status: str) -> SafeString:
    return _badge(WAYBILL_STATUS_CONFIG, status)


@register.simple_tag
def driver_status_badge(status: str) -> SafeString:
    return _badge(DRIVER_STATUS_CONFIG, status)


@register.simple_tag
def settlement_status_badge(status: str) -> SafeString:
    return _badge(SETTLEMENT_STATUS_CONFIG, status)


@register.simple_tag
def advance_status_badge(status: str) -> SafeString:
    return _badge(ADVANCE_STATUS_CONFIG, status)


# ============================================================
# SIDEBAR LINK
# ============================================================


@register.simple_tag(takes_context=True)
def sidebar_link(
    context: template.Context,
    request,
    url_name: str,
    *,
    icon: str = "",
    label: str = "",
    exact: bool = False,
) -> SafeString:
    """
    Renderiza link de sidebar com active state automático.

    Uso:
      {% sidebar_link request 'dashboard:index' icon='chart-bar' label='Dashboard' exact=True %}
      {% sidebar_link request 'operations:waybill-list' icon='document-text' label='Romaneios' %}
    """
    try:
        url = reverse(url_name)
    except NoReverseMatch:
        url = "#"

    current_path = request.path if request else ""

    if url == "#":
        is_active = False
    elif exact:
        is_active = current_path == url
    else:
        is_active = current_path.startswith(url) and url != "/"

    base = (
        "group flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium "
        "transition-colors duration-150 "
    )
    state = (
        "bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-400"
        if is_active
        else (
            "text-gray-600 hover:bg-gray-100 hover:text-gray-900 "
            "dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-gray-200"
        )
    )

    return format_html(
        '<a href="{}" class="{}{}">{}<span>{}</span></a>',
        url,
        base,
        state,
        _sidebar_icon(icon, is_active),
        label,
    )


def _sidebar_icon(icon_name: str, is_active: bool) -> SafeString:
    """SVG Heroicons outline para os ícones da sidebar."""
    cls = (
        "h-5 w-5 shrink-0 text-green-600 dark:text-green-500"
        if is_active
        else "h-5 w-5 shrink-0 text-gray-400 group-hover:text-gray-600 dark:group-hover:text-gray-300"
    )

    icons: dict[str, str] = {
        # ── Operações ──────────────────────────────────────────────
        "chart-bar": (
            '<svg class="{cls}" fill="none" viewBox="0 0 24 24" stroke="currentColor">'
            '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" '
            'd="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/>'
            "</svg>"
        ),
        "document-text": (
            '<svg class="{cls}" fill="none" viewBox="0 0 24 24" stroke="currentColor">'
            '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" '
            'd="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>'
            "</svg>"
        ),
        "calendar": (
            '<svg class="{cls}" fill="none" viewBox="0 0 24 24" stroke="currentColor">'
            '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" '
            'd="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/>'
            "</svg>"
        ),
        "map": (
            '<svg class="{cls}" fill="none" viewBox="0 0 24 24" stroke="currentColor">'
            '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" '
            'd="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7"/>'
            "</svg>"
        ),
        # ── Logística ──────────────────────────────────────────────
        "users": (
            '<svg class="{cls}" fill="none" viewBox="0 0 24 24" stroke="currentColor">'
            '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" '
            'd="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857'
            "M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857"
            "m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z"
            'm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"/>'
            "</svg>"
        ),
        "user-group": (  # alias de compatibilidade
            '<svg class="{cls}" fill="none" viewBox="0 0 24 24" stroke="currentColor">'
            '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" '
            'd="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857'
            "M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857"
            "m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z"
            'm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"/>'
            "</svg>"
        ),
        "truck": (
            '<svg class="{cls}" fill="none" viewBox="0 0 24 24" stroke="currentColor">'
            '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" '
            'd="M9 17a2 2 0 11-4 0 2 2 0 014 0zM19 17a2 2 0 11-4 0 2 2 0 014 0z"/>'
            '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" '
            'd="M13 16V6a1 1 0 00-1-1H4a1 1 0 00-1 1v10l2 2h10M13 16l2 2h4'
            'a1 1 0 001-1v-5.586a1 1 0 00-.293-.707l-2.414-2.414A1 1 0 0016.586 8H13"/>'
            "</svg>"
        ),
        "fire": (
            '<svg class="{cls}" fill="none" viewBox="0 0 24 24" stroke="currentColor">'
            '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" '
            'd="M17.657 18.657A8 8 0 016.343 7.343S7 9 9 10c0-2 .5-5 2.986-7'
            'C14 5 16.09 5.777 17.656 7.343A7.975 7.975 0 0120 13a7.975 7.975 0 01-2.343 5.657z"/>'
            '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" '
            'd="M9.879 16.121A3 3 0 1012.015 11L11 14H9c0 .768.293 1.536.879 2.121z"/>'
            "</svg>"
        ),
        # ── Financeiro ─────────────────────────────────────────────
        "currency-dollar": (
            '<svg class="{cls}" fill="none" viewBox="0 0 24 24" stroke="currentColor">'
            '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" '
            'd="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2'
            "m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1"
            'm0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>'
            "</svg>"
        ),
        "cash": (
            '<svg class="{cls}" fill="none" viewBox="0 0 24 24" stroke="currentColor">'
            '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" '
            'd="M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2'
            "m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2z"
            'm7-5a2 2 0 11-4 0 2 2 0 014 0z"/>'
            "</svg>"
        ),
        "clipboard-check": (
            '<svg class="{cls}" fill="none" viewBox="0 0 24 24" stroke="currentColor">'
            '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" '
            'd="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2'
            'M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"/>'
            "</svg>"
        ),
        # ── Relatórios / Utilitários ────────────────────────────────
        "document-report": (
            '<svg class="{cls}" fill="none" viewBox="0 0 24 24" stroke="currentColor">'
            '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" '
            'd="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2'
            'h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>'
            "</svg>"
        ),
        "cog": (
            '<svg class="{cls}" fill="none" viewBox="0 0 24 24" stroke="currentColor">'
            '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" '
            'd="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066'
            "c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35"
            "a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37"
            "a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0"
            "a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37"
            "a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35"
            "a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37"
            '.996.608 2.296.07 2.572-1.065z"/>'
            '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" '
            'd="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>'
            "</svg>"
        ),
    }

    svg_template = icons.get(
        icon_name,
        # Fallback: hamburguer genérico
        (
            '<svg class="{cls}" fill="none" viewBox="0 0 24 24" stroke="currentColor">'
            '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" '
            'd="M4 6h16M4 12h16M4 18h16"/>'
            "</svg>"
        ),
    )
    return mark_safe(svg_template.replace("{cls}", cls))


# ============================================================
# FILTERS — FORMATAÇÃO
# ============================================================


@register.filter
def currency_br(value) -> str:
    """
    Formata valor como moeda brasileira: R$ 1.234,56

    Usa Decimal para evitar erros de arredondamento de float
    (ex: float(1234.999) → R$ 1.234,100 sem Decimal).
    Suporta valores negativos: -R$ 500,00
    """
    if value is None:
        return "R$ 0,00"
    try:
        # Converte para Decimal com precisão controlada
        d = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        sign = "-" if d < 0 else ""
        abs_d = abs(d)
        # Separa inteiro e centavos
        int_part = int(abs_d)
        cents = int((abs_d - int_part) * 100)
        # Formata inteiro com separador de milhar
        int_str = f"{int_part:,}".replace(",", ".")
        return f"{sign}R$ {int_str},{cents:02d}"
    except (InvalidOperation, ValueError, TypeError):
        return "R$ 0,00"


@register.filter
def kg_to_tons(value) -> str:
    """
    Converte kg para toneladas no formato brasileiro: 1.234,567 t
    Usa 3 casas decimais — padrão de romaneios agrícolas.
    """
    if value is None:
        return "0,000 t"
    try:
        tons = Decimal(str(value)) / Decimal("1000")
        tons_rounded = tons.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
        # Formata com separadores brasileiros
        formatted = (
            f"{tons_rounded:,.3f}".replace(",", "X").replace(".", ",").replace("X", ".")
        )
        return f"{formatted} t"
    except (InvalidOperation, ValueError, TypeError):
        return "0,000 t"


@register.filter
def floatformat_br(value, decimal_places: int = 2) -> str:
    """
    Formata número decimal no padrão brasileiro.
    Útil para percentuais, quantidades e outros valores numéricos.

    Uso:
      {{ value|floatformat_br }}        → "1.234,56"
      {{ value|floatformat_br:3 }}      → "1.234,567"
      {{ value|floatformat_br:0 }}      → "1.234"
    """
    if value is None:
        return "0"
    try:
        places = max(0, int(decimal_places))
        quantize_str = "0." + "0" * places if places > 0 else "0"
        d = Decimal(str(value)).quantize(Decimal(quantize_str), rounding=ROUND_HALF_UP)
        formatted = (
            f"{d:,.{places}f}".replace(",", "X").replace(".", ",").replace("X", ".")
        )
        return formatted
    except (InvalidOperation, ValueError, TypeError):
        return "0"


@register.filter
def initials(name: str) -> str:
    """
    Retorna iniciais de um nome para avatares.
    'João da Silva' → 'JS' | 'Maria' → 'MA' | '' → '?'
    """
    if not name:
        return "?"
    parts = [p for p in name.strip().split() if p]
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return f"{parts[0][0]}{parts[-1][0]}".upper()


@register.filter
def absolute(value) -> Decimal:
    """Valor absoluto de um número."""
    try:
        return abs(Decimal(str(value)))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal("0")


@register.filter
def percentage(value, total) -> str:
    """
    Calcula percentual no formato brasileiro.

    Uso: {{ valor|percentage:total }} → "75,3%"
    """
    try:
        if not total:
            return "0,0%"
        pct = (Decimal(str(value)) / Decimal(str(total)) * 100).quantize(
            Decimal("0.1"), rounding=ROUND_HALF_UP
        )
        return f"{pct:.1f}%".replace(".", ",")
    except (InvalidOperation, ValueError, TypeError, ZeroDivisionError):
        return "0,0%"


@register.filter
def dict_get(d: dict, key: str):
    """Acessa dict com chave variável no template: {{ mydict|dict_get:key }}"""
    if isinstance(d, dict):
        return d.get(key)
    return None


@register.filter
def add_class(field, css_class: str):
    """Adiciona classe CSS a um field de formulário Django."""
    return field.as_widget(attrs={"class": css_class})


# ============================================================
# INCLUSION TAGS
# ============================================================


@register.inclusion_tag("partials/pagination.html", takes_context=True)
def render_pagination(
    context: template.Context,
    page_obj,
    anchor: str = "",
    htmx_target: str = "",
) -> dict:
    """
    Renderiza paginação reutilizável com suporte a HTMX.

    Uso:
      {% render_pagination page_obj %}
      {% render_pagination page_obj htmx_target="#waybill-table" %}
      {% render_pagination page_obj "#top" "#driver-list" %}
    """
    request = context.get("request")
    params = request.GET.copy() if request else {}
    params.pop("page", None)

    return {
        "page_obj": page_obj,
        "request": request,
        "query_params": params.urlencode(),
        "anchor": anchor,
        "htmx_target": htmx_target,
    }
