from django.urls import path

from .views.driver import (
    DriverCreateView,
    DriverDeactivateView,
    DriverDetailView,
    DriverListView,
    DriverUpdateView,
)
from .views.fueling import (
    FuelingCreateView,
    FuelingDetailView,
    FuelingListView,
    FuelingUpdateView,
)
from .views.proprietario import (
    ProprietarioCreateView,
    ProprietarioDeactivateView,
    ProprietarioDetailView,
    ProprietarioListView,
    ProprietarioUpdateView,
)
from .views.vehicle import (
    VehicleCreateView,
    VehicleDetailView,
    VehicleListView,
    VehicleUpdateView,
)

app_name = "logistics"

urlpatterns = [
    # Motoristas
    path("motoristas/", DriverListView.as_view(), name="driver-list"),
    path("motoristas/novo/", DriverCreateView.as_view(), name="driver-create"),
    path("motoristas/<uuid:pk>/", DriverDetailView.as_view(), name="driver-detail"),
    path("motoristas/<uuid:pk>/editar/", DriverUpdateView.as_view(), name="driver-update"),
    path(
        "motoristas/<uuid:pk>/inativar/", DriverDeactivateView.as_view(), name="driver-deactivate"
    ),
    # Proprietários
    path("proprietarios/", ProprietarioListView.as_view(), name="proprietario-list"),
    path("proprietarios/novo/", ProprietarioCreateView.as_view(), name="proprietario-create"),
    path("proprietarios/<uuid:pk>/", ProprietarioDetailView.as_view(), name="proprietario-detail"),
    path("proprietarios/<uuid:pk>/editar/", ProprietarioUpdateView.as_view(), name="proprietario-update"),
    path(
        "proprietarios/<uuid:pk>/inativar/",
        ProprietarioDeactivateView.as_view(),
        name="proprietario-deactivate",
    ),
    # Veículos
    path("veiculos/", VehicleListView.as_view(), name="vehicle-list"),
    path("veiculos/novo/", VehicleCreateView.as_view(), name="vehicle-create"),
    path("veiculos/<uuid:pk>/", VehicleDetailView.as_view(), name="vehicle-detail"),
    path("veiculos/<uuid:pk>/editar/", VehicleUpdateView.as_view(), name="vehicle-update"),
    # Abastecimentos
    path("abastecimentos/", FuelingListView.as_view(), name="fueling-list"),
    path("abastecimentos/novo/", FuelingCreateView.as_view(), name="fueling-create"),
    path("abastecimentos/<uuid:pk>/", FuelingDetailView.as_view(), name="fueling-detail"),
    path("abastecimentos/<uuid:pk>/editar/", FuelingUpdateView.as_view(), name="fueling-update"),
]
