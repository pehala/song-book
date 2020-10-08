"""Backend app URL Configuration"""
from django.urls import path

from category.views import CategorySongsListView, CategoryListView, CategoryCreateView, CategoryUpdateView, \
    CategoryDeleteView

urlpatterns = [
    path('', CategoryListView.as_view(), name="list"),
    path('add', CategoryCreateView.as_view(), name="add"),
    path('edit/<int:pk>', CategoryUpdateView.as_view(), name="edit"),
    path('delete/<int:pk>', CategoryDeleteView.as_view(), name="delete"),
    path('<str:slug>', CategorySongsListView.as_view(), name="index"),
]
