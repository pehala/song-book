"""Url configuration for PDF app"""
from django.urls import path

from pdf.views import RequestListView, RequestSongSelectorView, RequestNumberSelectView, RequestRemoveFileView

urlpatterns = [
    path('list', RequestListView.as_view(), name="list"),
    path('new', RequestSongSelectorView.as_view(), name="new"),
    path('assign', RequestNumberSelectView.as_view(), name="assign"),
    path('remove_file/<int:pk>', RequestRemoveFileView.as_view(), name="remove_file")
]
