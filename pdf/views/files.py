"""PDFFile related views"""

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.http import JsonResponse, Http404
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import ListView, DetailView
from django.views.generic.detail import SingleObjectMixin

from backend.generic import UniversalDeleteView, UniversalUpdateView
from backend.mixins import LocalAdminRequired
from category.forms import NameForm
from pdf.forms import PDFFileEditForm
from pdf.models import Status
from pdf.models.request import PDFFile, ManualPDFTemplate
from tenants.utils import tenant_cache_key
from tenants.views import AdminMoveView


class FileListView(LocalAdminRequired, ListView):
    """Lists all the files"""

    model = PDFFile
    template_name = "pdf/files/list.html"
    context_object_name = "files"

    def get_queryset(self):
        return super().get_queryset().filter(tenant=self.request.tenant)


class FileDeleteView(LocalAdminRequired, UniversalDeleteView):
    """Deletes File"""

    model = PDFFile
    success_url = reverse_lazy("pdf:files:list")

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        cache.delete(tenant_cache_key(self.object.tenant, settings.PDF_CACHE_KEY))
        return response


class FileUpdateView(LocalAdminRequired, UniversalUpdateView):
    """Updates File"""

    form_class = PDFFileEditForm
    model = PDFFile
    success_url = reverse_lazy("pdf:files:list")

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        cache.delete(tenant_cache_key(self.object.tenant, settings.PDF_CACHE_KEY))
        return response


class WaitForFileView(DetailView):
    """Shows wait page for PDF generation"""

    model = PDFFile
    context_object_name = "pdf"
    template_name = "pdf/files/wait.html"


class RenderInfoView(View, SingleObjectMixin):
    """Returns JSON response containing info about PDFFile"""

    model = PDFFile

    def get(self, request, *args, **kwargs):
        """Process GET request"""
        pdf_file = self.get_object()
        ready = pdf_file.status == Status.DONE
        return JsonResponse(
            {
                "ready": ready,
                "progress": pdf_file.progress,
                "link": pdf_file.file.url if ready else None,
                "scheduled_at": pdf_file.scheduled_at,
            }
        )


class MovePDFTemplatesView(AdminMoveView):
    """Moves Templates to a different Tenant"""

    formset_form = NameForm
    model = ManualPDFTemplate

    def action(self, target, ids):
        requests = ManualPDFTemplate.objects.filter(id__in=ids).distinct()
        with transaction.atomic():
            for request in requests:
                request.tenant = target
            ManualPDFTemplate.objects.bulk_update(requests, ["tenant"])

class FileTemplateEditView(LocalAdminRequired, SingleObjectMixin, View):
    """Redirects to correct edit page based on the class of the template"""

    model = PDFFile

    def get(self, request, *args, **kwargs):
        """Process GET request"""
        file = self.get_object()
        if file.template:
            template = file.template
            if isinstance(template, ManualPDFTemplate):
                return redirect("pdf:templates:edit", pk=template.pk)
            return redirect("category:edit", pk=template.pk)
        return Http404(_(f"File {file.id} does not have a template"))
