"""Url configuration for PDF app"""
from django.urls import path

from pdf.views import PDFSongs

urlpatterns = [
    path('export', PDFSongs.as_view(), name="export"),
]
