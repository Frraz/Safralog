"""
SafraLog — apps/logistics/views/vehicle.py
Views de Veículos.
"""

from __future__ import annotations

from decimal import Decimal

from django import forms
from django.contrib import messages
from django.db.models import Count, DecimalField, Sum
from django.db.models.functions import Coalesce
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View

from apps.core.mixins import RoleRequiredMixin, TenantRequiredMixin
from apps.operations.models import Waybill

from ..models import Driver, Vehicle

_ZERO = Decimal("0")


# ── Form ──────────────────────────────────────────────────────────────────────


class VehicleForm(forms.ModelForm):
    class Meta:
        model = Vehicle
        fields = [
            "plate",
            "vehicle_type",
            "brand",
            "model",
            "year",
            "color",
            "payload_kg",
            "status",
            "default_driver",
            "notes",
        ]
        widgets = {"notes": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, tenant=None, **kwargs):
        super().__init__(*args, **kwargs)
        if tenant:
            self.fields["default_driver"].queryset = Driver.objects.filter(
                tenant=tenant, is_active=True, status="active"
            ).order_by("name")
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "input")
        self.fields["default_driver"].required = False
        self.fields["color"].required = False
        self.fields["year"].required = False
        self.fields["notes"].required = False
        self.fields["payload_kg"].required = False


# ── Views ─────────────────────────────────────────────────────────────────────


class VehicleListView(TenantRequiredMixin, View):
    template_name = "logistics/vehicle/list.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        vehicles = (
            Vehicle.objects.filter(tenant=request.tenant, is_active=True)
            .select_related("default_driver")
            .order_by("plate")
        )
        q = request.GET.get("q", "").strip()
        if q:
            vehicles = vehicles.filter(plate__icontains=q)

        return render(request, self.template_name, {"vehicles": vehicles, "q": q})


class VehicleDetailView(TenantRequiredMixin, View):
    template_name = "logistics/vehicle/detail.html"

    def get(self, request: HttpRequest, pk) -> HttpResponse:
        vehicle = get_object_or_404(
            Vehicle.objects.select_related("default_driver"),
            pk=pk,
            tenant=request.tenant,
            is_active=True,
        )

        today = timezone.localdate()
        month_start = today.replace(day=1)

        # FIX: Coalesce fallback deve ser Decimal("0"), não int 0.
        # Sum("gross_weight") retorna DecimalField; o literal 0 é IntegerField.
        # Misturar os dois causa FieldError "Expression contains mixed types".
        stats = Waybill.objects.filter(
            tenant=request.tenant,
            vehicle=vehicle,
            is_active=True,
            status__in=["confirmed", "settled"],
            operation_date__gte=month_start,
        ).aggregate(
            month_waybills=Count("id"),
            month_gross=Coalesce(Sum("gross_weight"), _ZERO, output_field=DecimalField()),
            month_tare=Coalesce(Sum("tare_weight"), _ZERO, output_field=DecimalField()),
        )
        stats["month_net_tons"] = (stats["month_gross"] - stats["month_tare"]) / Decimal("1000")

        recent_waybills = (
            Waybill.objects.filter(tenant=request.tenant, vehicle=vehicle, is_active=True)
            .select_related("driver", "field")
            .order_by("-operation_date")[:10]
        )

        return render(
            request,
            self.template_name,
            {
                "vehicle": vehicle,
                "stats": stats,
                "recent_waybills": recent_waybills,
                "can_edit": request.user.role in ("admin", "manager"),
            },
        )


class VehicleCreateView(RoleRequiredMixin, View):
    required_roles = ["admin", "manager"]
    template_name = "logistics/vehicle/form.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        return render(
            request,
            self.template_name,
            {"form": VehicleForm(tenant=request.tenant), "action": "create"},
        )

    def post(self, request: HttpRequest) -> HttpResponse:
        form = VehicleForm(request.POST, tenant=request.tenant)
        if form.is_valid():
            vehicle = form.save(commit=False)
            vehicle.tenant = request.tenant
            vehicle.save()
            messages.success(request, f"Veículo {vehicle.plate} cadastrado.")
            return redirect("logistics:vehicle-detail", pk=vehicle.pk)
        return render(request, self.template_name, {"form": form, "action": "create"})


class VehicleUpdateView(RoleRequiredMixin, View):
    required_roles = ["admin", "manager"]
    template_name = "logistics/vehicle/form.html"

    def get(self, request: HttpRequest, pk) -> HttpResponse:
        vehicle = get_object_or_404(Vehicle, pk=pk, tenant=request.tenant, is_active=True)
        return render(
            request,
            self.template_name,
            {
                "form": VehicleForm(instance=vehicle, tenant=request.tenant),
                "vehicle": vehicle,
                "action": "edit",
            },
        )

    def post(self, request: HttpRequest, pk) -> HttpResponse:
        vehicle = get_object_or_404(Vehicle, pk=pk, tenant=request.tenant, is_active=True)
        form = VehicleForm(request.POST, instance=vehicle, tenant=request.tenant)
        if form.is_valid():
            form.save()
            messages.success(request, f"Veículo {vehicle.plate} atualizado.")
            return redirect("logistics:vehicle-detail", pk=vehicle.pk)
        return render(
            request,
            self.template_name,
            {"form": form, "vehicle": vehicle, "action": "edit"},
        )
