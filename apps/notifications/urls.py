from django.urls import path

from .views import MarkAllReadView, MarkReadView, NotificationListView, NotificationsDropdownView

app_name = "notifications"

urlpatterns = [
    path("", NotificationListView.as_view(), name="list"),
    path("dropdown/", NotificationsDropdownView.as_view(), name="dropdown"),
    path("<uuid:pk>/lida/", MarkReadView.as_view(), name="mark-read"),
    path("todas-lidas/", MarkAllReadView.as_view(), name="mark-all-read"),
]
