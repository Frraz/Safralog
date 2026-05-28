from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from simple_history.admin import SimpleHistoryAdmin
from unfold.admin import ModelAdmin

from .models import User


@admin.register(User)
class UserAdmin(ModelAdmin, BaseUserAdmin, SimpleHistoryAdmin):
    list_display = ["email", "full_name", "role", "tenant", "is_active", "last_seen_at"]
    list_filter = ["role", "tenant", "is_active", "is_superuser"]
    search_fields = ["email", "first_name", "last_name"]
    ordering = ["email"]
    readonly_fields = ["last_seen_at", "date_joined", "last_login"]

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Informações pessoais", {"fields": ("first_name", "last_name", "phone", "avatar")}),
        ("Tenant & Permissões", {"fields": ("tenant", "role", "is_active", "is_staff", "is_superuser")}),
        ("Preferências", {"fields": ("timezone",)}),
        ("Datas", {"fields": ("last_login", "date_joined", "last_seen_at")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "password1", "password2", "tenant", "role"),
        }),
    )
