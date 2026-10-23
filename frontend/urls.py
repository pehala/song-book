"""Frontend URL configuration"""

from django.urls import path

from frontend.views import ManifestView, ServiceWorkerView

urlpatterns = [
    path("sw.js", ServiceWorkerView.as_view(), name="sw"),
    path("manifest.webmanifest", ManifestView.as_view(), name="manifest"),
]
