"""Backend app URL Configuration."""

from django.urls import path

from category.views import (
    AllSongsUpdateView,
    CategoryCreateView,
    CategoryDeleteView,
    CategoryListView,
    CategoryMoveView,
    CategoryUpdateView,
)
from frontend.views import ShellView

urlpatterns = [
    path("", CategoryListView.as_view(), name="list"),
    path("add", CategoryCreateView.as_view(), name="add"),
    path("edit/<int:pk>", CategoryUpdateView.as_view(), name="edit"),
    path("delete/<int:pk>", CategoryDeleteView.as_view(), name="delete"),
    path("move", CategoryMoveView.as_view(), name="move"),
    path("all/edit", AllSongsUpdateView.as_view(), name="edit_all"),
    path("<str:slug>", ShellView.as_view(), name="index"),
]
