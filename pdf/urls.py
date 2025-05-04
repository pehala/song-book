"""Url configuration for PDF app"""

from django.urls import path, include

from pdf.views.files import (
    RenderInfoView,
    FileDeleteView,
    FileUpdateView,
    FileListView,
    MovePDFTemplatesView,
    WaitForFileView, FileTemplateEditView,
)
from pdf.views.templates import (
    UpdateTemplateView,
    TemplateListView,
    TemplateDeleteView,
    TemplateNumberSelectView,
    GenerateFromTemplateView,
)

template_patterns = [
    path("", TemplateListView.as_view(), name="list"),
    path("new", UpdateTemplateView.as_view(), name="new"),
    path("edit/<int:pk>", UpdateTemplateView.as_view(), name="edit"),
    path("delete/<int:pk>", TemplateDeleteView.as_view(), name="delete"),
    path("assign/<int:pk>", TemplateNumberSelectView.as_view(), name="assign"),
    path("<int:pk>/generate", GenerateFromTemplateView.as_view(), name="generate"),
    path("move", MovePDFTemplatesView.as_view(), name="move"),
]

file_patterns = [
    path("wait/<int:pk>", WaitForFileView.as_view(), name="wait"),
    path("info/<int:pk>", RenderInfoView.as_view(), name="info"),
    path("delete/<int:pk>", FileDeleteView.as_view(), name="delete"),
    path("edit/<int:pk>", FileUpdateView.as_view(), name="edit"),
    path("template/edit/<int:pk>", FileTemplateEditView.as_view(), name="template_edit"),
    path("", FileListView.as_view(), name="list"),
]

urlpatterns = [
    path("templates/", include((template_patterns, "pdf"), namespace="templates")),
    path("files/", include((file_patterns, "pdf"), namespace="files")),
]
