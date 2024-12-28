"""(Manual)PDFTemplate related views"""

from typing import Iterable

from django.contrib import messages
from django.db import transaction
from django.db.models import Count
from django.forms import formset_factory
from django.shortcuts import redirect, render
from django.urls import reverse_lazy, reverse
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import ListView, TemplateView
from django.views.generic.detail import SingleObjectMixin

from backend.generic import UniversalDeleteView
from backend.mixins import LocalAdminRequired
from backend.models import Song
from category.models import Category
from pdf.forms import PDFSongForm, BasePDFSongFormset, ManualTemplateForm, SongSelectionForm
from pdf.generate import AllowedTemplates, generate_pdf_file
from pdf.models import PDFTemplate
from pdf.models.request import ManualPDFTemplate


class TemplateListView(LocalAdminRequired, ListView):
    """Lists all the requests"""

    model = ManualPDFTemplate
    template_name = "pdf/templates/list.html"
    context_object_name = "templates"

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(tenant=self.request.tenant)
            .annotate(song_count=Count("songs"))
            .annotate(file_count=Count("pdffile"))
        )


class TemplateDeleteView(LocalAdminRequired, UniversalDeleteView):
    """Removes Template"""

    model = ManualPDFTemplate
    success_url = reverse_lazy("pdf:templates:list")


class GenerateFromTemplateView(LocalAdminRequired, View, SingleObjectMixin):
    """Regenerates the PDF request"""

    model = PDFTemplate

    # pylint: disable=unused-argument
    def get(self, request, pk):
        """Processes the request"""
        obj: AllowedTemplates = self.get_object()
        latest_file = obj.latest_file
        if obj.has_scheduled_file():
            messages.error(
                request,
                _("Another file %(id)s for %(name)s is already in queue") % {"id": latest_file.id, "name": obj.name},
            )
            return redirect("pdf:templates:list")
        file = generate_pdf_file(obj)
        messages.success(
            request,
            _("Scheduled File (%(id)s) generation from template %(template)s") % {"id": file.id, "template": obj.name},
        )
        return redirect("pdf:files:wait", pk=file.id)


class TemplateNumberingMixin:
    """Enables rendering of assign template with all required parameters"""

    PDFSongFormset = formset_factory(PDFSongForm, formset=BasePDFSongFormset, min_num=1, validate_min=True, extra=0)

    def render_assign_template(self, pk=None, formset=None, songs: Iterable[Song] | None = None):
        """Renders assign template"""
        formset = formset or self.PDFSongFormset(
            prefix="songs",
            initial=[
                {"name": song.name, "song_number": number, "song": song} for number, song in enumerate(songs, start=1)
            ],
        )
        pk = pk or self.kwargs.get("pk")
        assign_url = reverse("pdf:templates:assign", kwargs={"pk": pk})
        return render(self.request, "pdf/templates/assign.html", {"formset": formset, "action": assign_url})


class UpdateTemplateView(LocalAdminRequired, TemplateNumberingMixin, TemplateView):
    """Starts process of creating new PDFRequest by selecting songs for the request"""

    PREFIX = "template"
    context_object_name = "songs"
    template_name = "pdf/templates/select.html"

    def get_context_data(self, *, object_list=None, template_form=None, songs_form=None, **kwargs):
        ctx = super().get_context_data(object_list=object_list, **kwargs)

        songs = []
        if not template_form:
            if "pk" in self.kwargs:
                template = ManualPDFTemplate.objects.get(pk=self.kwargs["pk"], tenant=self.request.tenant)
                songs = list(template.songs.values_list("id", flat=True).distinct())
                template_form = ManualTemplateForm(
                    instance=ManualPDFTemplate.objects.get(pk=self.kwargs["pk"], tenant=self.request.tenant),
                    prefix=self.PREFIX,
                )
            else:
                template_form = ManualTemplateForm(
                    initial={"tenant": self.request.tenant, "locale": self.request.LANGUAGE_CODE},
                    prefix=self.PREFIX,
                )
        ctx["template_form"] = template_form

        if not songs_form:
            songs_form = SongSelectionForm(initial={"songs": songs}, request=self.request)
        ctx["songs_form"] = songs_form
        ctx["songs"] = songs_form.queryset
        ctx["initial_songs"] = songs_form.get_list_field_value("songs", [])

        queryset = Category.objects.filter(tenant=self.request.tenant).all()
        ctx["categories"] = queryset
        ctx["slugs"] = list(queryset.values_list("slug", flat=True))
        return ctx

    def post(self, request, *args, **kwargs):
        """Handles post request, shows assign.html to user to assign numbers to requested songs"""
        template_form = ManualTemplateForm(self.request.POST, request.FILES, prefix=self.PREFIX)
        songs_form = SongSelectionForm(self.request.POST, request.FILES, request=self.request)
        if template_form.is_valid() and songs_form.is_valid():
            template = template_form.instance
            template.tenant = self.request.tenant
            template.pdftemplate_ptr_id = self.kwargs.get("pk", None)
            template_form.save()
            if "pk" in self.kwargs:
                messages.success(
                    self.request,
                    _("File Template '%(name)s' was successfully updated") % {"name": template.name},
                )
            else:
                messages.success(
                    self.request,
                    _("File Template '%(name)s' was successfully created") % {"name": template.name},
                )
            return self.render_assign_template(pk=template_form.instance.pk, songs=songs_form.cleaned_data["songs"])
        return self.render_to_response(self.get_context_data(template_form=template_form, songs_form=songs_form))


class TemplateNumberSelectView(LocalAdminRequired, TemplateNumberingMixin, View):
    """Assign song numbers for PDF request"""

    PDFSongFormset = formset_factory(PDFSongForm, formset=BasePDFSongFormset, min_num=1, validate_min=True, extra=0)

    def get(self, *args, **kwargs):
        """Redirect back to the start of the process"""
        return redirect(reverse("pdf:templates:edit", kwargs={"pk": self.kwargs.get("pk")}))

    # pylint: disable=unused-argument
    def post(self, request, *args, **kwargs):
        """POST request method handler"""
        template = ManualPDFTemplate.objects.get(pk=self.kwargs["pk"])
        formset = self.PDFSongFormset(self.request.POST, prefix="songs")
        if formset.is_valid():
            with transaction.atomic():
                template.songs.clear()
                for form in formset:
                    form.instance.request = template
                    form.save()
            messages.success(
                self.request,
                _("Songs in File Template '%(name)s' were successfully updated") % {"name": template.name},
            )
            return redirect("pdf:templates:list")
        return self.render_assign_template(formset)
