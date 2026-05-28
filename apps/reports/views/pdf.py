"""
SafraLog — apps/reports/views/pdf.py
Geração de PDFs via WeasyPrint 63.x.

Decisões:
- base_url aponta para MEDIA_ROOT (filesystem) — WeasyPrint resolve
  caminhos de imagem via file:// sem depender de servidor HTTP.
- Imagens de anexo usam att.file.path (caminho absoluto no container).
- CSS embutido nos templates — sem dependência de arquivos estáticos externos.
"""

from __future__ import annotations

import io
from decimal import Decimal

from django.conf import settings
from django.db.models import DecimalField, Sum
from django.db.models.functions import Coalesce
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404
from django.views import View

from apps.core.mixins import TenantRequiredMixin

_ZERO = Decimal("0")


def render_pdf(template_name: str, context: dict, filename: str) -> HttpResponse:
    """
    Renderiza template HTML como PDF (WeasyPrint 63.x).

    base_url=MEDIA_ROOT garante que imagens referenciadas com
    file:// + path absoluto sejam resolvidas corretamente no container.
    """
    from django.template.loader import render_to_string
    from weasyprint import CSS, HTML
    from weasyprint.text.fonts import FontConfiguration

    html_string = render_to_string(template_name, context)
    font_config = FontConfiguration()

    html = HTML(
        string=html_string,
        base_url=str(settings.MEDIA_ROOT),  # FIX: era "/" — não resolvia assets
    )

    css = CSS(
        string="""
        @page {
            size: A4;
            margin: 1.5cm 2cm;
        }
        body {
            font-family: -apple-system, system-ui, sans-serif;
            font-size: 10pt;
            color: #111827;
        }
        @media print {
            .no-print { display: none !important; }
        }
        """,
        font_config=font_config,
    )

    buffer = io.BytesIO()
    html.write_pdf(buffer, stylesheets=[css], font_config=font_config)
    buffer.seek(0)

    response = HttpResponse(buffer.read(), content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="{filename}"'
    return response


class WaybillPDFView(TenantRequiredMixin, View):
    """PDF de romaneio individual."""

    def get(self, request: HttpRequest, pk) -> HttpResponse:
        from django.contrib.contenttypes.models import ContentType

        from apps.attachments.models import Attachment
        from apps.operations.models import Waybill

        waybill = get_object_or_404(
            Waybill.objects.select_related("driver", "vehicle", "field", "harvest", "tenant"),
            pk=pk,
            tenant=request.tenant,
        )

        ct = ContentType.objects.get_for_model(Waybill)
        attachments = Attachment.objects.filter(
            content_type=ct,
            object_id=str(waybill.pk),
            tenant=request.tenant,
            is_active=True,
            attachment_type="image",
        )

        return render_pdf(
            template_name="reports/pdf/waybill.html",
            context={
                "waybill": waybill,
                "attachments": attachments,
                "tenant": request.tenant,
            },
            filename=f"romaneio-{waybill.number:05d}.pdf",
        )


class SettlementPDFView(TenantRequiredMixin, View):
    """PDF de acerto financeiro."""

    def get(self, request: HttpRequest, pk) -> HttpResponse:
        from apps.finance.models import Settlement

        settlement = get_object_or_404(
            Settlement.objects.select_related("account", "approved_by"),
            pk=pk,
            tenant=request.tenant,
        )

        ledger_entries = settlement.account.entries.filter(
            competence_date__gte=settlement.period_start,
            competence_date__lte=settlement.period_end,
            is_reversed=False,
            is_active=True,
        ).order_by("competence_date", "entry_type")

        # FIX: UUID formatado legível para exibição no PDF
        settlement_id = str(settlement.pk).replace("-", "")[:8].upper()

        return render_pdf(
            template_name="reports/pdf/settlement.html",
            context={
                "settlement": settlement,
                "settlement_id": settlement_id,
                "ledger_entries": ledger_entries,
                "tenant": request.tenant,
            },
            filename=f"acerto-{settlement_id}.pdf",
        )


class WaybillExportView(TenantRequiredMixin, View):
    """Exportação de lista de romaneios como PDF."""

    def get(self, request: HttpRequest) -> HttpResponse:
        from django.db.models import Q

        from apps.operations.models import Waybill

        qs = Waybill.objects.filter(tenant=request.tenant, is_active=True).select_related(
            "driver", "vehicle", "harvest", "field"
        )

        status = request.GET.get("status")
        driver_id = request.GET.get("driver")
        date_start = request.GET.get("date_start")
        date_end = request.GET.get("date_end")
        q = request.GET.get("q", "").strip()

        if status:
            qs = qs.filter(status=status)
        if driver_id:
            qs = qs.filter(driver_id=driver_id)
        if date_start:
            qs = qs.filter(operation_date__gte=date_start)
        if date_end:
            qs = qs.filter(operation_date__lte=date_end)
        if q:
            qs = qs.filter(Q(number__icontains=q) | Q(driver__name__icontains=q))

        qs = qs.order_by("-operation_date")[:500]

        # FIX: Coalesce com output_field=DecimalField() — padrão obrigatório do projeto
        agg = qs.aggregate(
            total_gross=Coalesce(Sum("gross_weight"), _ZERO, output_field=DecimalField()),
            total_tare=Coalesce(Sum("tare_weight"), _ZERO, output_field=DecimalField()),
        )
        total_net = agg["total_gross"] - agg["total_tare"]

        return render_pdf(
            template_name="reports/pdf/waybill_list.html",
            context={
                "waybills": qs,
                "summary": {
                    "total_gross": agg["total_gross"],
                    "total_tare": agg["total_tare"],
                    "total_net": total_net,
                    "total_tons": total_net / Decimal("1000"),
                    "count": qs.count(),
                },
                "tenant": request.tenant,
                "filters": {
                    "status": status,
                    "date_start": date_start,
                    "date_end": date_end,
                },
            },
            filename="romaneios-exportacao.pdf",
        )
