"""
Views de conta de usuário.
"""
from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views import View


class ProfileView(LoginRequiredMixin, View):
    """Página de perfil do usuário logado."""

    template_name = "accounts/profile.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        return render(request, self.template_name, {"user": request.user})


class ProfileUpdateView(LoginRequiredMixin, View):
    """Edição de dados do perfil."""

    template_name = "accounts/profile_edit.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        from .forms import ProfileForm
        form = ProfileForm(instance=request.user)
        return render(request, self.template_name, {"form": form})

    def post(self, request: HttpRequest) -> HttpResponse:
        from .forms import ProfileForm
        from django.shortcuts import redirect

        form = ProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Perfil atualizado com sucesso.")
            return redirect("accounts:profile")
        return render(request, self.template_name, {"form": form})
