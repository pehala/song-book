"""Views for PDF app"""

from django.conf import settings
from django.contrib import messages
from django.core.cache import cache
from django.db import transaction
from django.db.models import Subquery, OuterRef
from django.forms import formset_factory
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import redirect
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView
from django.views.generic.base import TemplateResponseMixin, View
from django.views.generic.detail import SingleObjectMixin, DetailView

from backend.mixins import LocalAdminRequired
from backend.models import Song
from category.models import Category
from category.views import CategoryMoveView
from pdf.forms import RequestForm, PDFSongForm, BasePDFSongFormset, FileForm
from pdf.generate import generate_pdf_job
from pdf.models.request import PDFRequest, RequestType, Status


class RequestListView(LocalAdminRequired, ListView):
    """Lists all the requests"""

    model = PDFRequest
    template_name = "pdf/requests/list.html"
    context_object_name = "requests"

    def get_queryset(self):
        return super().get_queryset().filter(tenant=self.request.tenant)

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(object_list=object_list, **kwargs)
        context["automated"] = PDFRequest.objects.filter(category__tenant=self.request.tenant)
        return context


class RequestRegenerateView(LocalAdminRequired, View, SingleObjectMixin):
    """Regenerates the PDF request"""

    model = PDFRequest

    # pylint: disable=invalid-name, unused-argument
    def get(self, request, pk):
        """Processes the request"""
        obj = self.get_object()
        if obj.status == Status.QUEUED:
            messages.error(request, _("Request %(id)s is already in queue") % {"id": obj.id})
            return redirect("pdf:list")
        obj.status = Status.QUEUED
        obj.save()
        generate_pdf_job(obj)

        messages.success(request, _("Request %(id)s was scheduled for regeneration") % {"id": obj.id})
        return redirect("pdf:list")


class RequestRemoveFileView(LocalAdminRequired, View, SingleObjectMixin):
    """Removes file from request"""

    model = PDFRequest

    # pylint: disable=invalid-name, unused-argument
    def get(self, request, pk):
        """Processes the request"""
        obj = self.get_object()
        if not obj.file:
            messages.error(
                request,
                _("Unable to remove file from request %(id)s that doesn't have one") % {"id": obj.id},
            )
            return redirect("pdf:list")
        name = obj.file.name
        obj.file.delete()
        obj.save()

        messages.success(request, _("File %(name)s was successfully deleted") % {"name": name})
        cache.delete(settings.PDF_CACHE_KEY)
        return redirect("pdf:list")


class RequestSongSelectorView(LocalAdminRequired, ListView):
    """Starts process of creating new PDFRequest by selecting songs for the request"""

    model = Song
    context_object_name = "songs"
    template_name = "pdf/requests/select.html"

    def get_queryset(self):
        return super().get_queryset().filter(categories__tenant=self.request.tenant)

    def get_context_data(self, *, object_list=None, **kwargs):
        ctx = super().get_context_data(object_list=object_list, **kwargs)
        categories = list(Category.objects.filter(tenant=self.request.tenant).all())
        ctx["categories"] = categories
        ctx["slugs"] = list(map(lambda c: c.slug, categories))
        return ctx


class RequestNumberSelectView(LocalAdminRequired, TemplateResponseMixin, View):
    """Assign song numbers for PDF request"""

    template_name = "pdf/requests/assign.html"
    PDFSongFormset = formset_factory(PDFSongForm, formset=BasePDFSongFormset, min_num=1, validate_min=True, extra=0)

    def render_to_response(self, context, **response_kwargs):
        context.update()
        return super().render_to_response(context, **response_kwargs)

    # pylint: disable=unused-argument
    def get(self, request, *args, **kwargs):
        """GET request method handler"""
        if "songs" not in request.GET:
            return HttpResponseBadRequest(_("Required parameters not found"))

        songs_ids = request.GET.getlist("songs")
        songs = Song.objects.filter(id__in=songs_ids)
        if songs.count() == 0:
            return HttpResponseBadRequest(_("You need to select at least one song"))

        form = RequestForm(instance=PDFRequest(type=RequestType.MANUAL, tenant=self.request.tenant), prefix="request")
        formset = self.PDFSongFormset(
            prefix="songs",
            initial=[{"name": song.name, "song_number": number + 1, "song": song} for number, song in enumerate(songs)],
        )
        return self.render_to_response({"form": form, "formset": formset})

    # pylint: disable=unused-argument
    def post(self, request, *args, **kwargs):
        """POST request method handler"""
        form = RequestForm(self.request.POST, request.FILES, prefix="request")
        formset = self.PDFSongFormset(self.request.POST, prefix="songs")
        if form.is_valid() and formset.is_valid():
            request = form.instance
            request.type = RequestType.MANUAL
            request.tenant = self.request.tenant
            with transaction.atomic():
                request.save()
                for form in formset:
                    form.instance.request = request
                    form.instance.save()
            messages.success(
                self.request,
                _("PDF Request with id %(id)s was successfully created") % {"id": request.id},
            )
            generate_pdf_job(request)
            return redirect("pdf:wait", request.id)
        return self.form_invalid(form, formset)

    def form_invalid(self, form, formset):
        """If the form is invalid, render the invalid form."""
        return self.render_to_response({"form": form, "formset": formset})


class WaitForPDFView(DetailView):
    """Shows wait page for PDF generation"""

    model = PDFRequest
    context_object_name = "pdf"
    template_name = "pdf/requests/wait.html"


class RenderInfoView(View, SingleObjectMixin):
    """Returns JSON response containing info about PDFRequest"""

    model = PDFRequest

    def get(self, request, *args, **kwargs):
        """Process GET request"""
        request = self.get_object()
        ready = request.status == Status.DONE
        return JsonResponse(
            {
                "ready": request.status == Status.DONE,
                "progress": request.progress,
                "link": request.file.url if ready else None,
            }
        )


class RequestMoveView(CategoryMoveView):
    """Moves Requests to a different Tenant"""

    template_name = "admin/pdf/migrate.html"
    formset_class = formset_factory(FileForm, extra=0)

    def initial(self, pks):
        query = PDFRequest.objects.filter(id__in=pks)

        form = self.form_class()
        initial = []
        for category in query.values_list("id", "file", "title"):
            initial.append({"pk": category[0], "file": category[1], "title": category[2]})

        formset = self.formset_class(initial=initial)
        return form, formset

    def action(self, tenant, ids):
        requests = PDFRequest.objects.filter(id__in=ids).distinct()
        with transaction.atomic():
            for request in requests:
                request.tenant = tenant
            PDFRequest.objects.bulk_update(requests, ["tenant"])
