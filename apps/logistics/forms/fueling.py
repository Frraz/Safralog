"""
Formulário de Abastecimento.
"""
from django import forms
from ..models import Driver, Fueling, Vehicle


class FuelingForm(forms.ModelForm):
    class Meta:
        model = Fueling
        fields = [
            "driver", "vehicle", "harvest",
            "fueling_date", "fuel_type", "liters",
            "posted_price_per_liter", "driver_price_per_liter", "extras_amount",
            "payment_method",
            "odometer", "station_name", "notes",
        ]
        widgets = {
            "fueling_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "notes": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, tenant=None, **kwargs):
        super().__init__(*args, **kwargs)
        if tenant:
            self.fields["driver"].queryset = (
                Driver.objects.filter(tenant=tenant, is_active=True, status="active")
                .order_by("name")
            )
            self.fields["vehicle"].queryset = (
                Vehicle.objects.filter(tenant=tenant, is_active=True)
                .order_by("plate")
            )
            from apps.operations.models import Harvest
            self.fields["harvest"].queryset = (
                Harvest.objects.filter(tenant=tenant, is_active=True, status="active")
            )

        for name, field in self.fields.items():
            if isinstance(field.widget, forms.Textarea):
                field.widget.attrs.setdefault("class", "input")
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs.setdefault("class", "input")
            else:
                field.widget.attrs.setdefault("class", "input")

        self.fields["vehicle"].required = False
        self.fields["harvest"].required = False
        self.fields["posted_price_per_liter"].required = False
        self.fields["extras_amount"].required = False
        self.fields["odometer"].required = False
        self.fields["station_name"].required = False
        self.fields["notes"].required = False
        self.fields["posted_price_per_liter"].label = "Preço do posto (R$/L) — opcional"
        self.fields["driver_price_per_liter"].label = "Preço descontado do motorista (R$/L) *"
        self.fields["extras_amount"].label = "Outros produtos no cupom (R$)"
