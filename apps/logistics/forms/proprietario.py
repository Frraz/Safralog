"""
Formulário de Proprietário do Caminhão.
"""
from django import forms

from ..models import Driver, Proprietario


class ProprietarioForm(forms.ModelForm):
    class Meta:
        model = Proprietario
        fields = [
            "name",
            "document",
            "phone",
            "driver",
            "bank_name",
            "bank_agency",
            "bank_account",
            "bank_account_type",
            "pix_key",
            "pix_key_type",
            "notes",
        ]
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, tenant=None, **kwargs):
        super().__init__(*args, **kwargs)

        if tenant is not None:
            self.fields["driver"].queryset = Driver.objects.filter(
                tenant=tenant,
                is_active=True,
            ).order_by("name")

        for field in self.fields.values():
            if isinstance(field.widget, forms.Textarea):
                field.widget.attrs.setdefault("class", "input")
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs.setdefault("class", "input")
            else:
                field.widget.attrs.setdefault("class", "input")

        # Campos opcionais
        for fname in ["document", "phone", "driver", "bank_name", "bank_agency",
                      "bank_account", "pix_key", "pix_key_type", "notes"]:
            self.fields[fname].required = False

        # Labels PT-BR claros
        self.fields["driver"].label = "Motorista (se o proprietário também dirige)"
        self.fields["driver"].help_text = (
            "Vincule ao motorista somente quando o proprietário e o motorista são a mesma pessoa."
        )
        self.fields["bank_account_type"].required = False
        self.fields["bank_account_type"].label = "Tipo de conta bancária"
