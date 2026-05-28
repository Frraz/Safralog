"""
SafraLog — apps/notifications/views.py
"""

from __future__ import annotations

from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views import View

from apps.core.mixins import TenantRequiredMixin

from .models import Notification


class NotificationListView(TenantRequiredMixin, View):
    template_name = "notifications/list.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        notifications = Notification.objects.filter(user=request.user).order_by("-created_at")[:50]
        return render(
            request,
            self.template_name,
            {
                "notifications": notifications,
            },
        )


class NotificationsDropdownView(TenantRequiredMixin, View):
    template_name = "notifications/_list.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        notifications = Notification.objects.filter(user=request.user).order_by("-created_at")[:10]
        return render(
            request,
            self.template_name,
            {
                "notifications": notifications,
            },
        )


class MarkReadView(TenantRequiredMixin, View):
    def post(self, request: HttpRequest, pk) -> HttpResponse:
        notification = get_object_or_404(Notification, pk=pk, user=request.user)
        notification.is_read = True
        notification.save(update_fields=["is_read"])
        # Retorna partial atualizada para HTMX
        notifications = Notification.objects.filter(user=request.user).order_by("-created_at")[:10]
        return render(
            request,
            "notifications/_list.html",
            {
                "notifications": notifications,
            },
        )


class MarkAllReadView(TenantRequiredMixin, View):
    def post(self, request: HttpRequest) -> HttpResponse:
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        notifications = Notification.objects.filter(user=request.user).order_by("-created_at")[:10]
        return render(
            request,
            "notifications/_list.html",
            {
                "notifications": notifications,
            },
        )
