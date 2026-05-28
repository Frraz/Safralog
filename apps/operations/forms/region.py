"""
Formulário de Região de Origem.
"""
from django import forms

from ..models import Region


class RegionForm(forms.ModelForm):
    class Meta:
        model = Region
        fields = ["name", "default_price_per_ton", "description"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.Textarea):
                field.widget.attrs.setdefault("class", "input")
            else:
                field.widget.attrs.setdefault("class", "input")
        self.fields["description"].required = False
        self.fields["default_price_per_ton"].widget.attrs["step"] = "0.01"
        self.fields["default_price_per_ton"].widget.attrs["placeholder"] = "Ex.: 80.00"
