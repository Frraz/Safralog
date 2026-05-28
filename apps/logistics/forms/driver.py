"""
Formulário de Motorista.
"""
from django import forms
from ..models import Driver


class DriverForm(forms.ModelForm):
    class Meta:
        model = Driver
        fields = [
            "name", "document_cpf", "document_cnh",
            "cnh_category", "cnh_expiry", "phone", "status", "photo", "notes",
        ]
        widgets = {
            "cnh_expiry": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.Textarea):
                field.widget.attrs.setdefault("class", "input")
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs.setdefault("class", "input")
            else:
                field.widget.attrs.setdefault("class", "input")
        self.fields["notes"].required = False
        self.fields["document_cnh"].required = False
        self.fields["cnh_category"].required = False
        self.fields["cnh_expiry"].required = False
        self.fields["photo"].required = False
