"""Analytics URLs configuration"""

from django.urls import path

from analytics.views import AnalyticsRestView, AnalyticsShowView, HitView

urlpatterns = [
    path("", AnalyticsShowView.as_view(), name="index"),
    path("hit/<str:key>", HitView.as_view(), name="hit"),
    path("data", AnalyticsRestView.as_view(), name="data"),
]
