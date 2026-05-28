"""
Formulário de Romaneio (Waybill).
"""

from __future__ import annotations

from django import forms
from django.urls import reverse_lazy

from apps.logistics.models import Driver, Vehicle
from apps.operations.models import Field, Harvest, Waybill


class WaybillForm(forms.ModelForm):
    """
    Formulário completo de romaneio.
    Filtra choices pelo tenant para isolamento multi-tenant.
    """

    class Meta:
        model = Waybill
        fields = [
            "harvest",
            "field",
            "driver",
            "vehicle",
            "culture",
            "operation_date",
            "operation_time",
            "gross_weight",
            "tare_weight",
            "unit_price",
            "destination",
            "scale_ticket",
            "notes",
        ]
        widgets = {
            "operation_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "operation_time": forms.TimeInput(attrs={"type": "time"}, format="%H:%M"),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, tenant=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.tenant = tenant

        if tenant:
            self.fields["harvest"].queryset = Harvest.objects.filter(tenant=tenant, status="active")
            self.fields["field"].queryset = Field.objects.filter(
                tenant=tenant, is_active=True
            ).select_related("harvest", "region")
            self.fields["driver"].queryset = Driver.objects.filter(
                tenant=tenant, is_active=True, status="active"
            ).order_by("name")
            self.fields["vehicle"].queryset = Vehicle.objects.filter(
                tenant=tenant, is_active=True, status="active"
            ).order_by("plate")

        # HTMX: ao mudar o talhão, busca o preço padrão da região
        self.fields["field"].widget.attrs.update({
            "hx-get": reverse_lazy("operations:waybill-region-price"),
            "hx-target": "#id_unit_price",
            "hx-swap": "outerHTML",
            "hx-trigger": "change",
        })

        # Aplicar classes CSS a todos os campos
        for field_name, field in self.fields.items():
            widget = field.widget
            existing = widget.attrs.get("class", "")
            if isinstance(widget, forms.Textarea):
                widget.attrs["class"] = f"input {existing}".strip()
            elif isinstance(widget, forms.Select):
                widget.attrs["class"] = f"input {existing}".strip()
            elif isinstance(widget, forms.CheckboxInput):
                widget.attrs["class"] = "rounded border-gray-300"
            else:
                widget.attrs["class"] = f"input {existing}".strip()

        # Campos opcionais
        self.fields["field"].required = False
        self.fields["operation_time"].required = False
        self.fields["destination"].required = False
        self.fields["scale_ticket"].required = False
        self.fields["notes"].required = False

    def clean(self):
        cleaned_data = super().clean()
        gross = cleaned_data.get("gross_weight")
        tare = cleaned_data.get("tare_weight")

        if gross and tare and tare >= gross:
            self.add_error("tare_weight", "Tara deve ser menor que o peso bruto.")

        return cleaned_data
