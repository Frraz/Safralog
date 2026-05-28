from django.urls import path

from . import views

app_name = "attachments"

urlpatterns = [
    path("upload/", views.AttachmentUploadView.as_view(), name="upload"),
    path("<uuid:pk>/delete/", views.AttachmentDeleteView.as_view(), name="delete"),
    path("list/", views.AttachmentListView.as_view(), name="list"),
]
