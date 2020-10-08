"""Backend app URL Configuration"""
from django.urls import path

from backend.views import SongCreateView, SongUpdateView, SongDeleteView, SongsDatatableView, \
    IndexSongListView

urlpatterns = [
    path('', IndexSongListView.as_view(), name="index"),
    path('add', SongCreateView.as_view(), name="add"),
    path('edit/<int:pk>', SongUpdateView.as_view(), name="edit"),
    path('delete/<int:pk>', SongDeleteView.as_view(), name="delete"),
    path('api/songs', SongsDatatableView.as_view(), name="songs"),
]
