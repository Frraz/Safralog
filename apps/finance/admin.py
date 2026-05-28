from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import Advance, FinancialAccount, LedgerEntry, Settlement


@admin.register(LedgerEntry)
class LedgerEntryAdmin(ModelAdmin):
    list_display = [
        "reference_code", "entry_type", "direction", "amount",
        "quantity", "competence_date", "is_reversed", "tenant"
    ]
    list_filter = ["entry_type", "direction", "is_reversed", "tenant"]
    search_fields = ["reference_code"]
    readonly_fields = [
        "reference_code", "amount", "quantity", "entry_type", "direction",
        "competence_date", "is_reversed", "reversal_entry", "created_at",
    ]
    date_hierarchy = "competence_date"

    def has_add_permission(self, request):
        return False  # Ledger imutável — não adicionar via admin

    def has_change_permission(self, request, obj=None):
        return False  # Ledger imutável


@admin.register(FinancialAccount)
class FinancialAccountAdmin(ModelAdmin):
    list_display = ["name", "account_type", "current_balance", "tenant"]
    list_filter = ["account_type", "tenant"]
    search_fields = ["name"]


@admin.register(Settlement)
class SettlementAdmin(ModelAdmin):
    list_display = [
        "account", "settlement_type", "status", "period_start",
        "period_end", "snapshot_net_balance", "tenant"
    ]
    list_filter = ["status", "settlement_type", "tenant"]
    readonly_fields = [
        "snapshot_total_production", "snapshot_total_credits",
        "snapshot_total_debits", "snapshot_net_balance",
        "snapshot_waybill_count", "closed_at", "approved_by", "approved_at",
    ]


@admin.register(Advance)
class AdvanceAdmin(ModelAdmin):
    list_display = ["driver", "amount", "payment_method", "status", "payment_date", "tenant"]
    list_filter = ["status", "payment_method", "tenant"]
    search_fields = ["driver__name", "reference_code"]
    date_hierarchy = "payment_date"
