"""
SafraLog — apps/dashboard/views.py
"""

from __future__ import annotations

from django.db.models import Q
from django.shortcuts import render
from django.views import View

from apps.core.mixins import HTMXMixin, TenantRequiredMixin

from .selectors import get_dashboard_stats


class DashboardView(TenantRequiredMixin, View):
    template_name = "dashboard/index.html"

    def get(self, request):
        context = get_dashboard_stats(request.tenant)
        return render(request, self.template_name, context)


class QuickSearchView(TenantRequiredMixin, HTMXMixin, View):
    """
    HTMX partial para a command palette.
    Busca motoristas, veículos e romaneios em tempo real.
    Retorna partial HTML renderizado no #search-results.
    """

    template_name = "dashboard/_quick_search.html"

    def get(self, request):
        query = request.GET.get("q", "").strip()
        drivers = []
        waybills = []
        vehicles = []

        if len(query) >= 2:
            from apps.logistics.models import Driver, Vehicle
            from apps.operations.models import Waybill

            # FIX: Q() em vez de | entre querysets separados — evita duplicatas
            # e permite buscar número do romaneio
            waybills = (
                Waybill.objects.filter(tenant=request.tenant, is_active=True)
                .filter(
                    Q(driver__name__icontains=query)
                    | Q(vehicle__plate__icontains=query)
                    | Q(number__icontains=query)
                    | Q(scale_ticket__icontains=query)
                )
                .select_related("driver", "vehicle", "field")
                .order_by("-operation_date")
                .distinct()[:6]
            )

            drivers = (
                Driver.objects.filter(tenant=request.tenant, is_active=True)
                .filter(Q(name__icontains=query) | Q(document_cpf__icontains=query))
                .order_by("name")[:4]
            )

            vehicles = (
                Vehicle.objects.filter(tenant=request.tenant, is_active=True)
                .filter(
                    Q(plate__icontains=query)
                    | Q(model__icontains=query)
                    | Q(brand__icontains=query)
                )
                .order_by("plate")[:4]
            )

        total = len(waybills) + len(drivers) + len(vehicles)

        return render(
            request,
            self.template_name,
            {
                "query": query,
                "waybills": waybills,
                "drivers": drivers,
                "vehicles": vehicles,
                "total": total,
                "has_results": total > 0,
            },
        )
