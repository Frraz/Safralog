from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin
from unfold.admin import ModelAdmin

from .models import Driver, Fueling, Vehicle


@admin.register(Driver)
class DriverAdmin(ModelAdmin, SimpleHistoryAdmin):
    list_display = ["name", "document_cpf", "status", "cnh_category", "cnh_expiry", "tenant"]
    list_filter = ["status", "cnh_category", "tenant"]
    search_fields = ["name", "document_cpf"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(Vehicle)
class VehicleAdmin(ModelAdmin, SimpleHistoryAdmin):
    list_display = ["plate", "vehicle_type", "brand", "model", "status", "tenant"]
    list_filter = ["vehicle_type", "status", "tenant"]
    search_fields = ["plate", "brand", "model"]


@admin.register(Fueling)
class FuelingAdmin(ModelAdmin):
    list_display = [
        "driver", "vehicle", "fuel_type", "liters",
        "driver_price_per_liter", "total_value", "fueling_date", "tenant"
    ]
    list_filter = ["fuel_type", "payment_method", "tenant"]
    search_fields = ["driver__name", "vehicle__plate", "station_name"]
    date_hierarchy = "fueling_date"
    readonly_fields = ["total_value", "created_at", "updated_at"]
