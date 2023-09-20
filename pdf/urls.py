"""Url configuration for PDF app"""
from django.urls import path

from pdf.views import (
    RequestListView,
    RequestSongSelectorView,
    RequestNumberSelectView,
    RequestRemoveFileView,
    RequestRegenerateView,
    WaitForPDFView,
    RenderInfoView,
    RequestMoveView,
)

urlpatterns = [
    path("list", RequestListView.as_view(), name="list"),
    path("new", RequestSongSelectorView.as_view(), name="new"),
    path("assign", RequestNumberSelectView.as_view(), name="assign"),
    path("wait/<int:pk>", WaitForPDFView.as_view(), name="wait"),
    path("info/<int:pk>", RenderInfoView.as_view(), name="info"),
    path("remove_file/<int:pk>", RequestRemoveFileView.as_view(), name="remove_file"),
    path("regenerate/<int:pk>", RequestRegenerateView.as_view(), name="regenerate"),
    path("move", RequestMoveView.as_view(), name="move"),
]
