"""PDFFile related views."""

from django.conf import settings
from django.core.cache import cache
from django.http import Http404, JsonResponse
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import DetailView, ListView
from django.views.generic.detail import SingleObjectMixin

from backend.generic import UniversalDeleteView, UniversalUpdateView
from backend.mixins import LocalAdminRequired, TenantObjectsMixin
from pdf.forms import PDFFileEditForm
from pdf.models import Status
from pdf.models.request import AllSongsTemplate, ManualPDFTemplate, PDFFile
from tenants.utils import tenant_cache_key


class FileListView(LocalAdminRequired, TenantObjectsMixin, ListView):
    """Lists all the files."""

    model = PDFFile
    template_name = "pdf/files/list.html"
    context_object_name = "files"


class FileDeleteView(LocalAdminRequired, TenantObjectsMixin, UniversalDeleteView):
    """Deletes File."""

    model = PDFFile
    success_url = reverse_lazy("pdf:files:list")

    def post(self, request, *args, **kwargs):
        """Deletes the file and drops the cached list of the tenant's PDFs."""
        response = super().post(request, *args, **kwargs)
        cache.delete(tenant_cache_key(self.object.tenant, settings.PDF_CACHE_KEY))
        return response


class FileUpdateView(LocalAdminRequired, TenantObjectsMixin, UniversalUpdateView):
    """Updates File."""

    form_class = PDFFileEditForm
    model = PDFFile
    success_url = reverse_lazy("pdf:files:list")

    def post(self, request, *args, **kwargs):
        """Updates the file and drops the cached list of the tenant's PDFs."""
        response = super().post(request, *args, **kwargs)
        cache.delete(tenant_cache_key(self.object.tenant, settings.PDF_CACHE_KEY))
        return response


class WaitForFileView(TenantObjectsMixin, DetailView):
    """Shows wait page for PDF generation; the browser polls `RenderInfoView` and draws the progress."""

    model = PDFFile
    context_object_name = "pdf"
    template_name = "pdf/files/wait.html"

    def get_context_data(self, **kwargs):
        """Adds the filename and the endpoint that reports the progress."""
        context = super().get_context_data(**kwargs)
        context["page"] = {
            "filename": self.object.filename,
            "info": reverse("pdf:files:info", kwargs={"pk": self.object.pk}),
        }
        return context


class RenderInfoView(TenantObjectsMixin, SingleObjectMixin, View):
    """Returns JSON response containing info about PDFFile."""

    model = PDFFile

    def get(self, request, *args, **kwargs):
        """Process GET request."""
        pdf_file = self.get_object()
        ready = pdf_file.status == Status.DONE
        return JsonResponse(
            {
                "ready": ready,
                "failed": pdf_file.status == Status.FAILED,
                "progress": pdf_file.progress,
                "link": pdf_file.file.url if ready else None,
                "scheduled_at": pdf_file.scheduled_at,
            }
        )


class FileTemplateEditView(LocalAdminRequired, TenantObjectsMixin, SingleObjectMixin, View):
    """Redirects to correct edit page based on the class of the template."""

    model = PDFFile

    def get(self, request, *args, **kwargs):
        """Process GET request."""
        file = self.get_object()
        if file.template:
            template = file.template
            if isinstance(template, ManualPDFTemplate):
                return redirect("pdf:templates:edit", pk=template.pk)
            if isinstance(template, AllSongsTemplate):
                return redirect("category:edit_all")
            return redirect("category:edit", pk=template.pk)
        raise Http404(_("File %(id)s does not have a template") % {"id": file.id})
