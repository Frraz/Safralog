"""
Admin de Operações — Safras, Talhões, Romaneios.
"""
from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin
from unfold.admin import ModelAdmin

from .models import Field, Harvest, Waybill


@admin.register(Harvest)
class HarvestAdmin(ModelAdmin, SimpleHistoryAdmin):
    list_display = ["name", "crop_type", "status", "start_date", "tenant", "is_active"]
    list_filter = ["status", "crop_type", "tenant"]
    search_fields = ["name"]
    ordering = ["-start_date"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(Field)
class FieldAdmin(ModelAdmin):
    list_display = ["name", "harvest", "area_ha", "tenant", "is_active"]
    list_filter = ["harvest", "tenant"]
    search_fields = ["name"]
    autocomplete_fields = ["harvest"]


@admin.register(Waybill)
class WaybillAdmin(ModelAdmin, SimpleHistoryAdmin):
    list_display = [
        "number", "driver", "harvest", "culture", "status",
        "operation_date", "net_weight", "total_value", "tenant",
    ]
    list_filter = ["status", "culture", "tenant", "operation_date"]
    search_fields = ["number", "driver__name", "scale_ticket"]
    readonly_fields = [
        "number", "net_weight", "net_weight_tons", "total_value",
        "created_at", "updated_at", "ledger_entry",
    ]
    autocomplete_fields = ["driver", "vehicle", "harvest", "field"]
    date_hierarchy = "operation_date"
    ordering = ["-operation_date", "-number"]
