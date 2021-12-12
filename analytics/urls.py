"""Analytics URLs configuration"""
from django.urls import path

from analytics.views import AnalyticsShowView, AnalyticsRestView

urlpatterns = [
    path('', AnalyticsShowView.as_view(), name="index"),
    path('data', AnalyticsRestView.as_view(), name="data"),
]
