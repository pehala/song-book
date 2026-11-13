"""Frontend URL configuration."""

from django.urls import path

from frontend.views import IconView, ManifestView, ServiceWorkerView

urlpatterns = [
    path("service_worker.js", ServiceWorkerView.as_view(), name="service_worker"),
    path("manifest.webmanifest", ManifestView.as_view(), name="manifest"),
    path("icons/<int:size>.png", IconView.as_view(), name="icon"),
    path("icons/<int:size>-maskable.png", IconView.as_view(maskable=True), name="icon_maskable"),
]
