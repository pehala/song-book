"""Analytics Application configuration"""
from django.apps import AppConfig


class AnalyticsConfig(AppConfig):
    """Analytics app"""

    default_auto_field = "django.db.models.BigAutoField"
    name = "analytics"
