"""Frontend URL configuration"""

from django.urls import path

from frontend.views import ManifestView, ServiceWorkerView

urlpatterns = [
    path("service_worker.js", ServiceWorkerView.as_view(), name="service_worker"),
    path("manifest.webmanifest", ManifestView.as_view(), name="manifest"),
]
