from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin
from unfold.admin import ModelAdmin

from .models import Tenant


@admin.register(Tenant)
class TenantAdmin(ModelAdmin, SimpleHistoryAdmin):
    list_display = ["name", "slug", "plan", "status", "max_users", "created_at"]
    list_filter = ["plan", "status"]
    search_fields = ["name", "slug", "document"]
    readonly_fields = ["slug", "created_at", "updated_at"]
    prepopulated_fields = {}  # slug é auto via save()
