"""
URLs de contas de usuário (além do allauth).
Perfil, troca de senha customizada, preferências.
"""
from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("perfil/", views.ProfileView.as_view(), name="profile"),
    path("perfil/editar/", views.ProfileUpdateView.as_view(), name="profile-update"),
]
