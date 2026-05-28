from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.DashboardView.as_view(), name="index"),
    path("quick-search/", views.QuickSearchView.as_view(), name="quick-search"),
]
