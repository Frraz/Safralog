"""
Mixins de views reutilizáveis do SafraLog.
"""
from __future__ import annotations

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views.generic import View


class TenantRequiredMixin(LoginRequiredMixin):
    """
    Exige usuário autenticado E com tenant ativo.
    Filtra automaticamente querysets por tenant.
    """

    def dispatch(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        response = super().dispatch(request, *args, **kwargs)
        if not request.user.is_authenticated:
            return response

        if not getattr(request, "tenant", None) and not request.user.is_superuser:
            raise PermissionDenied("Usuário sem tenant configurado.")

        return response

    def get_tenant(self):
        return getattr(self.request, "tenant", None)

    def get_queryset(self):
        qs = super().get_queryset()
        tenant = self.get_tenant()
        if tenant:
            qs = qs.filter(tenant=tenant)
        return qs


class RoleRequiredMixin(TenantRequiredMixin):
    """
    Exige um dos papéis definidos em `required_roles`.

    Uso:
        class MyView(RoleRequiredMixin, DetailView):
            required_roles = ["admin", "manager"]
    """

    required_roles: list[str] = []

    def dispatch(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        response = super().dispatch(request, *args, **kwargs)
        if not request.user.is_authenticated:
            return response

        if self.required_roles and not request.user.is_superuser:
            if not hasattr(request.user, "role") or request.user.role not in self.required_roles:
                raise PermissionDenied(
                    f"Papel necessário: {', '.join(self.required_roles)}"
                )

        return response


class HTMXMixin:
    """
    Detecta requisição HTMX e oferece helpers para respostas parciais.
    """

    request: HttpRequest

    @property
    def is_htmx(self) -> bool:
        return bool(getattr(self.request, "htmx", False))

    def htmx_redirect(self, url: str) -> HttpResponse:
        """Redireciona via HTMX (sem reload de página)."""
        response = HttpResponse(status=204)
        response["HX-Redirect"] = url
        return response

    def htmx_refresh(self) -> HttpResponse:
        """Força reload da página via HTMX."""
        response = HttpResponse(status=204)
        response["HX-Refresh"] = "true"
        return response

    def htmx_trigger(self, event: str, data: dict | None = None) -> HttpResponse:
        """Dispara evento HTMX no cliente."""
        import json
        response = HttpResponse(status=204)
        if data:
            response["HX-Trigger"] = json.dumps({event: data})
        else:
            response["HX-Trigger"] = event
        return response

    def get_template_names(self) -> list[str]:
        """
        Em requests HTMX, tenta usar template partial (_fragment.html).
        Fallback para template completo.
        """
        names = super().get_template_names()  # type: ignore[misc]
        if self.is_htmx:
            # Insere versão parcial antes do template completo
            partial_names = []
            for name in names:
                base, _, ext = name.rpartition(".")
                partial_names.append(f"{base}_fragment.{ext}")
            return partial_names + names
        return names


class SoftDeleteMixin:
    """
    Para views de delete: usa soft_delete() em vez de delete().
    Requer model com método soft_delete().
    """

    def delete(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        obj = self.get_object()  # type: ignore[attr-defined]
        if hasattr(obj, "soft_delete"):
            obj.soft_delete()
            if self.is_htmx:  # type: ignore[attr-defined]
                return HttpResponse(status=200)
            from django.shortcuts import redirect
            success_url = self.get_success_url()  # type: ignore[attr-defined]
            return redirect(success_url)
        return super().delete(request, *args, **kwargs)  # type: ignore[misc]


class JsonResponseMixin:
    """Helper para views que retornam JSON."""

    def json_success(self, data: dict | None = None, status: int = 200) -> JsonResponse:
        return JsonResponse({"ok": True, "data": data or {}}, status=status)

    def json_error(self, message: str, status: int = 400, errors: dict | None = None) -> JsonResponse:
        payload: dict = {"ok": False, "message": message}
        if errors:
            payload["errors"] = errors
        return JsonResponse(payload, status=status)
