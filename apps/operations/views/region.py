"""
SafraLog — apps/operations/views/region.py
Views de Regiões de Origem (preço por tonelada).
"""
from __future__ import annotations

from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from apps.core.mixins import HTMXMixin, RoleRequiredMixin, TenantRequiredMixin

from ..forms.region import RegionForm
from ..models import Region


class RegionListView(TenantRequiredMixin, View):
    template_name = "operations/region/list.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        regions = Region.objects.filter(tenant=request.tenant, is_active=True).order_by("name")
        return render(request, self.template_name, {"regions": regions})


class RegionCreateView(RoleRequiredMixin, HTMXMixin, View):
    required_roles = ["admin", "manager"]
    template_name = "operations/region/form.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        return render(request, self.template_name, {"form": RegionForm(), "action": "create"})

    def post(self, request: HttpRequest) -> HttpResponse:
        form = RegionForm(request.POST)

        if not form.is_valid():
            return render(request, self.template_name, {"form": form, "action": "create"})

        region = form.save(commit=False)
        region.tenant = request.tenant
        region.save()

        messages.success(request, f"Região '{region.name}' cadastrada — R$ {region.default_price_per_ton:.2f}/ton.")

        if self.is_htmx:
            return self.htmx_redirect(redirect("operations:region-list")["Location"])
        return redirect("operations:region-list")


class RegionUpdateView(RoleRequiredMixin, HTMXMixin, View):
    required_roles = ["admin", "manager"]
    template_name = "operations/region/form.html"

    def get(self, request: HttpRequest, pk) -> HttpResponse:
        region = get_object_or_404(Region, pk=pk, tenant=request.tenant, is_active=True)
        return render(request, self.template_name, {"form": RegionForm(instance=region), "region": region, "action": "edit"})

    def post(self, request: HttpRequest, pk) -> HttpResponse:
        region = get_object_or_404(Region, pk=pk, tenant=request.tenant, is_active=True)
        form = RegionForm(request.POST, instance=region)

        if not form.is_valid():
            return render(request, self.template_name, {"form": form, "region": region, "action": "edit"})

        form.save()
        messages.success(request, f"Região '{region.name}' atualizada.")

        if self.is_htmx:
            return self.htmx_redirect(redirect("operations:region-list")["Location"])
        return redirect("operations:region-list")


class RegionDeleteView(RoleRequiredMixin, HTMXMixin, View):
    required_roles = ["admin", "manager"]

    def post(self, request: HttpRequest, pk) -> HttpResponse:
        region = get_object_or_404(Region, pk=pk, tenant=request.tenant, is_active=True)

        talhoes_vinculados = region.fields.filter(is_active=True).count()
        if talhoes_vinculados:
            messages.error(
                request,
                f"A região '{region.name}' possui {talhoes_vinculados} talhão(ões) vinculado(s). "
                "Desvincule os talhões antes de excluir.",
            )
            if self.is_htmx:
                return self.htmx_refresh()
            return redirect("operations:region-list")

        region.soft_delete()
        messages.success(request, f"Região '{region.name}' excluída.")

        if self.is_htmx:
            return self.htmx_redirect(redirect("operations:region-list")["Location"])
        return redirect("operations:region-list")


class RegionPriceView(TenantRequiredMixin, View):
    """Endpoint HTMX: retorna fragment HTML com o preço padrão do talhão selecionado."""

    def get(self, request: HttpRequest) -> HttpResponse:
        field_id = request.GET.get("field")
        price = ""

        if field_id:
            from ..models import Field as FieldModel
            try:
                f = FieldModel.objects.select_related("region").get(
                    pk=field_id, tenant=request.tenant, is_active=True
                )
                if f.region_id:
                    price = str(f.region.default_price_per_ton)
            except FieldModel.DoesNotExist:
                pass

        # Retorna apenas o campo input para o HTMX substituir
        html = (
            f'<input type="number" name="unit_price" id="id_unit_price" '
            f'value="{price}" class="input" step="0.0001" min="0.0001" '
            f'placeholder="Ex.: 80.00" required>'
        )
        return HttpResponse(html)
