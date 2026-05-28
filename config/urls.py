"""
SafraLog — config/urls.py
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    # Admin
    path("admin/", admin.site.urls),
    # Health
    path("health/", include("health_check.urls")),
    # Accounts (allauth)
    path("accounts/", include("allauth.urls")),
    path("accounts/", include("apps.accounts.urls")),
    # Apps
    path("", include("apps.dashboard.urls")),
    path("operations/", include("apps.operations.urls")),
    path("logistics/", include("apps.logistics.urls")),
    path("finance/", include("apps.finance.urls")),
    path("attachments/", include("apps.attachments.urls")),
    path("relatorios/", include("apps.reports.urls")),
    path("notifications/", include("apps.notifications.urls", namespace="notifications")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

    try:
        import debug_toolbar

        urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns
    except ImportError:
        pass
