"""
SafraLog — apps/operations/urls.py
"""

from django.urls import path

from .views.field import FieldCreateView, FieldDetailView, FieldListView, FieldUpdateView
from .views.harvest import HarvestCreateView, HarvestDetailView, HarvestListView, HarvestUpdateView
from .views.region import RegionCreateView, RegionDeleteView, RegionListView, RegionPriceView, RegionUpdateView
from .views.waybill import (
    WaybillCancelView,
    WaybillConfirmView,
    WaybillCreateView,
    WaybillDetailView,
    WaybillListView,
    WaybillUpdateView,
)

app_name = "operations"

urlpatterns = [
    # Romaneios
    path("romaneios/", WaybillListView.as_view(), name="waybill-list"),
    path("romaneios/novo/", WaybillCreateView.as_view(), name="waybill-create"),
    path("romaneios/<uuid:pk>/", WaybillDetailView.as_view(), name="waybill-detail"),
    path("romaneios/<uuid:pk>/editar/", WaybillUpdateView.as_view(), name="waybill-update"),
    path("romaneios/<uuid:pk>/confirmar/", WaybillConfirmView.as_view(), name="waybill-confirm"),
    path("romaneios/<uuid:pk>/cancelar/", WaybillCancelView.as_view(), name="waybill-cancel"),
    path("romaneios/preco-por-talhao/", RegionPriceView.as_view(), name="waybill-region-price"),
    # Safras
    path("safras/", HarvestListView.as_view(), name="harvest-list"),
    path("safras/nova/", HarvestCreateView.as_view(), name="harvest-create"),
    path("safras/<uuid:pk>/", HarvestDetailView.as_view(), name="harvest-detail"),
    path("safras/<uuid:pk>/editar/", HarvestUpdateView.as_view(), name="harvest-update"),
    # Talhões
    path("talhoes/", FieldListView.as_view(), name="field-list"),
    path("talhoes/novo/", FieldCreateView.as_view(), name="field-create"),
    path("talhoes/<uuid:pk>/", FieldDetailView.as_view(), name="field-detail"),
    path("talhoes/<uuid:pk>/editar/", FieldUpdateView.as_view(), name="field-update"),
    # Regiões
    path("regioes/", RegionListView.as_view(), name="region-list"),
    path("regioes/nova/", RegionCreateView.as_view(), name="region-create"),
    path("regioes/<uuid:pk>/editar/", RegionUpdateView.as_view(), name="region-update"),
    path("regioes/<uuid:pk>/excluir/", RegionDeleteView.as_view(), name="region-delete"),
]
