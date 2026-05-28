from django.urls import path

from .views.advance import (
    AdvanceCancelView,
    AdvanceCreateView,
    AdvanceDetailView,
    AdvanceListView,
)
from .views.settlement import (
    SettlementApproveView,
    SettlementCancelView,
    SettlementCloseView,
    SettlementCreateView,
    SettlementDetailView,
    SettlementListView,
    SettlementMarkPaidView,
    SettlementOverrideValueView,
    SettlementSubmitView,
)

app_name = "finance"

urlpatterns = [
    # Fechamentos
    path("acertos/", SettlementListView.as_view(), name="settlement-list"),
    path("acertos/novo/", SettlementCreateView.as_view(), name="settlement-create"),
    path("acertos/<uuid:pk>/", SettlementDetailView.as_view(), name="settlement-detail"),
    path("acertos/<uuid:pk>/enviar/", SettlementSubmitView.as_view(), name="settlement-submit"),
    path("acertos/<uuid:pk>/aprovar/", SettlementApproveView.as_view(), name="settlement-approve"),
    path("acertos/<uuid:pk>/fechar/", SettlementCloseView.as_view(), name="settlement-close"),
    path("acertos/<uuid:pk>/cancelar/", SettlementCancelView.as_view(), name="settlement-cancel"),
    path("acertos/<uuid:pk>/pagar/", SettlementMarkPaidView.as_view(), name="settlement-mark-paid"),
    path("acertos/<uuid:pk>/ajuste/", SettlementOverrideValueView.as_view(), name="settlement-override"),
    # Adiantamentos
    path("adiantamentos/", AdvanceListView.as_view(), name="advance-list"),
    path("adiantamentos/novo/", AdvanceCreateView.as_view(), name="advance-create"),
    path("adiantamentos/<uuid:pk>/", AdvanceDetailView.as_view(), name="advance-detail"),
    path("adiantamentos/<uuid:pk>/cancelar/", AdvanceCancelView.as_view(), name="advance-cancel"),
]
