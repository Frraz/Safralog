"""
SafraLog — apps/attachments/models.py
Sistema de anexos genérico para qualquer entidade do sistema.
Suporta: imagens, PDFs, documentos.
Upload: drag-and-drop, Ctrl+V, câmera mobile.
"""
import os
import uuid

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import TenantModel


def attachment_upload_path(instance, filename):
    """
    Path dinâmico para uploads:
    attachments/{content_type}/{year}/{month}/{uuid}/{filename}
    """
    ext = os.path.splitext(filename)[1].lower()
    new_name = f"{uuid.uuid4().hex}{ext}"
    content_type_name = instance.content_type.model if instance.content_type else "misc"
    from django.utils import timezone
    now = timezone.now()
    return f"attachments/{content_type_name}/{now.year}/{now.month:02d}/{new_name}"


class Attachment(TenantModel):
    """
    Anexo genérico vinculado a qualquer entidade via GenericForeignKey.

    Uso:
        waybill.attachments.all()  — requer GenericRelation na model

    Upload direto do celular (câmera) é suportado via input[capture=environment].
    Ctrl+V e drag-and-drop são suportados via JS (static/js/upload.js).
    """

    class AttachmentType(models.TextChoices):
        IMAGE = "image", _("Imagem")
        PDF = "pdf", _("PDF")
        DOCUMENT = "document", _("Documento")
        SPREADSHEET = "spreadsheet", _("Planilha")
        OTHER = "other", _("Outro")

    # Referência genérica
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        verbose_name=_("Tipo de objeto"),
    )
    object_id = models.UUIDField(verbose_name=_("ID do objeto"))
    content_object = GenericForeignKey("content_type", "object_id")

    # Arquivo
    file = models.FileField(
        upload_to=attachment_upload_path,
        verbose_name=_("Arquivo"),
    )
    original_filename = models.CharField(
        max_length=255,
        verbose_name=_("Nome original"),
    )
    file_size = models.PositiveBigIntegerField(
        verbose_name=_("Tamanho (bytes)"),
        default=0,
    )
    mime_type = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name=_("MIME type"),
    )
    attachment_type = models.CharField(
        max_length=20,
        choices=AttachmentType.choices,
        default=AttachmentType.IMAGE,
        verbose_name=_("Tipo"),
        db_index=True,
    )

    # Metadados
    title = models.CharField(
        max_length=200,
        blank=True,
        default="",
        verbose_name=_("Título"),
        help_text=_("Descrição opcional do anexo"),
    )
    uploaded_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attachments",
        verbose_name=_("Enviado por"),
    )

    # Thumbnail (gerado assincronamente para imagens)
    thumbnail = models.ImageField(
        upload_to="attachments/thumbnails/%Y/%m/",
        blank=True,
        null=True,
        verbose_name=_("Thumbnail"),
    )

    class Meta(TenantModel.Meta):
        verbose_name = _("Anexo")
        verbose_name_plural = _("Anexos")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
            models.Index(fields=["attachment_type"]),
            models.Index(fields=["uploaded_by"]),
        ]

    def __str__(self):
        return self.original_filename or str(self.id)

    @property
    def is_image(self) -> bool:
        return self.attachment_type == self.AttachmentType.IMAGE

    @property
    def file_size_mb(self) -> float:
        return round(self.file_size / (1024 * 1024), 2)

    @property
    def file_url(self) -> str:
        try:
            return self.file.url
        except Exception:
            return ""

    @property
    def thumbnail_url(self) -> str:
        if self.thumbnail:
            try:
                return self.thumbnail.url
            except Exception:
                pass
        return self.file_url

    def save(self, *args, **kwargs):
        if self.file and not self.file_size:
            try:
                self.file_size = self.file.size
            except Exception:
                pass
        if not self.original_filename and self.file:
            self.original_filename = os.path.basename(self.file.name)
        super().save(*args, **kwargs)
