"""Backend app URL Configuration"""

from django.urls import path

from backend.views import (
    MeView,
    SongCreateView,
    SongDeleteView,
    SongsApiView,
    SongUpdateView,
)
from frontend.views import ShellView

urlpatterns = [
    path("", ShellView.as_view(), name="index"),
    path("add", SongCreateView.as_view(), name="add"),
    path("edit/<int:pk>", SongUpdateView.as_view(), name="edit"),
    path("delete/<int:pk>", SongDeleteView.as_view(), name="delete"),
    path("all", ShellView.as_view(), name="all"),
    path("api/me", MeView.as_view(), name="me"),
    path("api/songs", SongsApiView.as_view(), name="songs_api"),
]
