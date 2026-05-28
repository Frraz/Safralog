"""
Views de Attachments — upload assíncrono e deleção.
"""
from __future__ import annotations

import json

from django.contrib.contenttypes.models import ContentType
from django.http import HttpRequest, JsonResponse
from django.views import View
from django.views.decorators.http import require_http_methods

from apps.core.mixins import TenantRequiredMixin

from .models import Attachment


class AttachmentUploadView(TenantRequiredMixin, View):
    """
    POST /attachments/upload/
    Recebe arquivo via XHR (upload.js) e cria Attachment.
    Retorna JSON com dados do anexo criado.
    """

    def post(self, request: HttpRequest) -> JsonResponse:
        file = request.FILES.get("file")
        object_type = request.POST.get("object_type")
        object_id = request.POST.get("object_id")

        if not file:
            return JsonResponse({"error": "Nenhum arquivo enviado."}, status=400)

        if not object_type or not object_id:
            return JsonResponse({"error": "object_type e object_id são obrigatórios."}, status=400)

        # Resolve ContentType
        try:
            # object_type pode ser "waybill", "driver", etc.
            app_label, model = self._resolve_content_type(object_type)
            ct = ContentType.objects.get(app_label=app_label, model=model)
        except (ValueError, ContentType.DoesNotExist):
            return JsonResponse({"error": f"Tipo desconhecido: {object_type}"}, status=400)

        # Determina tipo de anexo pelo mime
        mime_type = file.content_type or ""
        attachment_type = self._get_attachment_type(mime_type)

        attachment = Attachment.objects.create(
            tenant=request.tenant,
            content_type=ct,
            object_id=object_id,
            file=file,
            original_filename=file.name,
            file_size=file.size,
            mime_type=mime_type,
            attachment_type=attachment_type,
            uploaded_by=request.user,
        )

        return JsonResponse({
            "id": str(attachment.pk),
            "name": attachment.original_filename,
            "url": attachment.file_url,
            "thumbnail_url": attachment.thumbnail_url,
            "is_image": attachment.is_image,
            "size": attachment.file_size,
            "type": attachment.attachment_type,
        }, status=201)

    def _resolve_content_type(self, object_type: str) -> tuple[str, str]:
        """Mapeia object_type para (app_label, model)."""
        mapping = {
            "waybill": ("operations", "waybill"),
            "driver": ("logistics", "driver"),
            "vehicle": ("logistics", "vehicle"),
            "fueling": ("logistics", "fueling"),
            "advance": ("finance", "advance"),
            "settlement": ("finance", "settlement"),
            "harvest": ("operations", "harvest"),
        }
        if object_type not in mapping:
            raise ValueError(f"Tipo desconhecido: {object_type}")
        return mapping[object_type]

    def _get_attachment_type(self, mime_type: str) -> str:
        if mime_type.startswith("image/"):
            return "image"
        if mime_type == "application/pdf":
            return "pdf"
        if "spreadsheet" in mime_type or "excel" in mime_type:
            return "spreadsheet"
        if "word" in mime_type or "document" in mime_type:
            return "document"
        return "other"


class AttachmentDeleteView(TenantRequiredMixin, View):
    """
    DELETE /attachments/<pk>/delete/
    Deleta o anexo (soft delete) e retorna 200.
    """

    def delete(self, request: HttpRequest, pk: str) -> JsonResponse:
        try:
            attachment = Attachment.objects.get(
                pk=pk,
                tenant=request.tenant,
                is_active=True,
            )
        except Attachment.DoesNotExist:
            return JsonResponse({"error": "Anexo não encontrado."}, status=404)

        attachment.soft_delete()
        return JsonResponse({"ok": True}, status=200)


class AttachmentListView(TenantRequiredMixin, View):
    """
    GET /attachments/?object_type=waybill&object_id=<uuid>
    Retorna HTML partial com lista de anexos do objeto.
    """

    template_name = "attachments/_list.html"

    def get(self, request: HttpRequest) -> "HttpResponse":
        from django.shortcuts import render

        object_type = request.GET.get("object_type")
        object_id = request.GET.get("object_id")

        attachments = []
        if object_type and object_id:
            try:
                ct = ContentType.objects.get_by_natural_key(
                    *self._resolve_content_type(object_type)
                )
                attachments = Attachment.objects.filter(
                    tenant=request.tenant,
                    content_type=ct,
                    object_id=object_id,
                    is_active=True,
                ).order_by("-created_at")
            except Exception:
                pass

        return render(request, self.template_name, {"attachments": attachments})
