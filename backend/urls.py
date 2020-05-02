"""Backend app URL Configuration"""
from django.urls import path

from backend import views

urlpatterns = [
    path('', views.index, name="index"),
    path('add', views.edit, {"primary_key": None}, name="add"),
    path('edit/<int:primary_key>', views.edit, name="edit"),
    path('delete/<int:primary_key>', views.delete, name="delete"),
]
