"""
Formulários de conta de usuário.
"""
from django import forms
from django.contrib.auth import get_user_model

User = get_user_model()


class ProfileForm(forms.ModelForm):
    """Edição de dados pessoais do usuário."""

    class Meta:
        model = User
        fields = ["first_name", "last_name", "phone", "avatar", "timezone"]
        widgets = {
            "timezone": forms.Select(
                choices=[
                    ("America/Sao_Paulo", "Brasília (GMT-3)"),
                    ("America/Manaus", "Manaus (GMT-4)"),
                    ("America/Belem", "Belém (GMT-3)"),
                    ("America/Fortaleza", "Fortaleza (GMT-3)"),
                    ("America/Recife", "Recife (GMT-3)"),
                    ("America/Bahia", "Salvador (GMT-3)"),
                    ("America/Cuiaba", "Cuiabá (GMT-4)"),
                    ("America/Porto_Velho", "Porto Velho (GMT-4)"),
                    ("America/Rio_Branco", "Rio Branco (GMT-5)"),
                ]
            )
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if isinstance(field.widget, (forms.TextInput, forms.Select)):
                field.widget.attrs.setdefault("class", "input")
        self.fields["avatar"].required = False
        self.fields["phone"].required = False
        self.fields["timezone"].required = False
