"""
Views de Talhões (Fields).
"""

from __future__ import annotations

from django import forms
from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from apps.core.mixins import RoleRequiredMixin, TenantRequiredMixin

from ..models import Field, Harvest, Waybill


class FieldForm(forms.ModelForm):
    class Meta:
        model = Field
        fields = ["harvest", "region", "name", "area_ha", "location_description", "notes"]
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 3}),
            "location_description": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, tenant=None, **kwargs):
        super().__init__(*args, **kwargs)
        if tenant:
            from ..models import Region
            self.fields["harvest"].queryset = Harvest.objects.filter(
                tenant=tenant, status="active"
            ).order_by("-start_date")
            self.fields["region"].queryset = Region.objects.filter(
                tenant=tenant, is_active=True
            ).order_by("name")
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "input")
        self.fields["region"].required = False
        self.fields["region"].label = "Região (define preço padrão por tonelada)"
        self.fields["location_description"].required = False
        self.fields["notes"].required = False
        self.fields["area_ha"].required = False


class FieldListView(TenantRequiredMixin, View):
    template_name = "operations/field/list.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        harvest_id = request.GET.get("harvest")
        fields = (
            Field.objects.filter(tenant=request.tenant, is_active=True)
            .select_related("harvest")
            .order_by("harvest__name", "name")
        )
        if harvest_id:
            fields = fields.filter(harvest_id=harvest_id)

        harvests = Harvest.objects.filter(tenant=request.tenant).order_by("-start_date")
        return render(
            request,
            self.template_name,
            {
                "fields": fields,
                "harvests": harvests,
                "harvest_filter": harvest_id,
            },
        )


class FieldDetailView(TenantRequiredMixin, View):
    template_name = "operations/field/detail.html"

    def get(self, request: HttpRequest, pk) -> HttpResponse:
        field = get_object_or_404(
            Field.objects.select_related("harvest"),
            pk=pk,
            tenant=request.tenant,
            is_active=True,
        )
        recent_waybills = (
            Waybill.objects.filter(tenant=request.tenant, field=field, is_active=True)
            .select_related("driver", "vehicle")
            .order_by("-operation_date")[:10]
        )
        return render(
            request,
            self.template_name,
            {
                "field": field,
                "recent_waybills": recent_waybills,
            },
        )


class FieldCreateView(RoleRequiredMixin, View):
    required_roles = ["admin", "manager"]
    template_name = "operations/field/form.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        return render(
            request,
            self.template_name,
            {"form": FieldForm(tenant=request.tenant), "action": "create"},
        )

    def post(self, request: HttpRequest) -> HttpResponse:
        form = FieldForm(request.POST, tenant=request.tenant)
        if form.is_valid():
            field = form.save(commit=False)
            field.tenant = request.tenant
            field.save()
            messages.success(request, f"Talhão '{field.name}' criado com sucesso.")
            return redirect("operations:field-detail", pk=field.pk)
        return render(request, self.template_name, {"form": form, "action": "create"})


class FieldUpdateView(RoleRequiredMixin, View):
    required_roles = ["admin", "manager"]
    template_name = "operations/field/form.html"

    def get(self, request: HttpRequest, pk) -> HttpResponse:
        field = get_object_or_404(Field, pk=pk, tenant=request.tenant, is_active=True)
        return render(
            request,
            self.template_name,
            {
                "form": FieldForm(instance=field, tenant=request.tenant),
                "field": field,
                "action": "edit",
            },
        )

    def post(self, request: HttpRequest, pk) -> HttpResponse:
        field = get_object_or_404(Field, pk=pk, tenant=request.tenant, is_active=True)
        form = FieldForm(request.POST, instance=field, tenant=request.tenant)
        if form.is_valid():
            form.save()
            messages.success(request, f"Talhão '{field.name}' atualizado.")
            return redirect("operations:field-detail", pk=field.pk)
        return render(request, self.template_name, {"form": form, "field": field, "action": "edit"})
