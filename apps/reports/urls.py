from django.urls import path

from .views.index import ReportsIndexView
from .views.pdf import SettlementPDFView, WaybillExportView, WaybillPDFView

app_name = "reports"

urlpatterns = [
    path("", ReportsIndexView.as_view(), name="index"),
    path("romaneio/<uuid:pk>/pdf/", WaybillPDFView.as_view(), name="waybill-pdf"),
    path("acerto/<uuid:pk>/pdf/", SettlementPDFView.as_view(), name="settlement-pdf"),
    path("romaneios/exportar/", WaybillExportView.as_view(), name="waybill-export"),
]
