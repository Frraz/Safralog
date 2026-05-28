"""
SafraLog — apps/reports/views/index.py
Página inicial de relatórios.
"""

from __future__ import annotations

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views import View

from apps.core.mixins import TenantRequiredMixin


class ReportsIndexView(TenantRequiredMixin, View):
    template_name = "reports/index.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        return render(request, self.template_name, {})
