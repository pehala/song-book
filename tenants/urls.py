"""URLs for Tenant"""

from django.urls import path

from tenants.views import TenantUpdateForm

urlpatterns = [
    path("edit", TenantUpdateForm.as_view(), name="edit"),
]
