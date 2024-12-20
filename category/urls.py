"""Backend app URL Configuration"""

from django.urls import path

from category.views import (
    CategorySongsListView,
    CategoryListView,
    CategoryCreateView,
    CategoryUpdateView,
    CategoryDeleteView,
    # CategoryRegeneratePDFView,
    CategoryMoveView,
)

urlpatterns = [
    path("", CategoryListView.as_view(), name="list"),
    path("add", CategoryCreateView.as_view(), name="add"),
    path("edit/<int:pk>", CategoryUpdateView.as_view(), name="edit"),
    path("delete/<int:pk>", CategoryDeleteView.as_view(), name="delete"),
    path("move", CategoryMoveView.as_view(), name="move"),
    path("<str:slug>", CategorySongsListView.as_view(), name="index"),
]
