"""
Authentication backend customizado do SafraLog.

Permite login por e-mail (em vez de username, padrão do Django).
O allauth já trata a maior parte do fluxo; este backend é um fallback
para autenticações diretas via django.contrib.auth.authenticate().
"""
from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

User = get_user_model()


class EmailOrUsernameBackend(ModelBackend):
    """
    Autentica por e-mail OU username.

    Prioridade:
      1. Tenta encontrar por e-mail (case-insensitive)
      2. Fallback para username (comportamento padrão do Django)

    Útil para chamadas diretas a authenticate() fora do fluxo allauth,
    como scripts de management, testes e integrações de API.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username or not password:
            return None

        # Tenta por e-mail
        try:
            user = User.objects.get(email__iexact=username)
        except User.DoesNotExist:
            # Tenta por username
            try:
                user = User.objects.get(username__iexact=username)
            except User.DoesNotExist:
                # Roda o hash mesmo sem usuário para evitar timing attacks
                User().set_password(password)
                return None
        except User.MultipleObjectsReturned:
            # E-mails duplicados — não autentica (problema de dados)
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user

        return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
