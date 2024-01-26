"""Tenant App configuration"""

from django.apps import AppConfig


class TenantsConfig(AppConfig):
    """Tenant Config"""

    default_auto_field = "django.db.models.BigAutoField"
    name = "tenants"
