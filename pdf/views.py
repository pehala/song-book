"""Views for PDF app"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.forms import formset_factory
from django.http import HttpResponseBadRequest, HttpResponseRedirect
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView
from django.views.generic.base import TemplateResponseMixin, View

from backend.models import Song
from pdf.forms import RequestForm, PDFSongForm, BasePDFSongFormset
from pdf.models import PDFRequest, RequestType


@method_decorator(login_required, name='dispatch')
class RequestListView(ListView):
    """Lists all the requests"""
    model = PDFRequest
    template_name = "pdf/requests/list.html"
    context_object_name = "requests"


@method_decorator(login_required, name='dispatch')
class RequestSongSelectorView(ListView):
    """Starts process of creating new PDFRequest by selecting songs for the request"""
    model = Song
    context_object_name = "songs"
    template_name = "pdf/requests/select.html"


@method_decorator(login_required, name='dispatch')
class RequestNumberSelectView(TemplateResponseMixin, View):
    """Assign song numbers for PDF request"""
    template_name = "pdf/requests/assign.html"
    success_url = reverse_lazy("pdf:list")
    PDFSongFormset = formset_factory(PDFSongForm,
                                     formset=BasePDFSongFormset,
                                     min_num=1,
                                     validate_min=True,
                                     extra=0)

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

        form = RequestForm(instance=PDFRequest(type=RequestType.MANUAL), prefix="request")
        formset = self.PDFSongFormset(prefix="songs",
                                      initial=[
                                          {'name': song.name,
                                           'song_number': number + 1,
                                           'song': song}
                                          for number, song
                                          in enumerate(songs)
                                      ])
        return self.render_to_response({"form": form, "formset": formset})

    # pylint: disable=unused-argument
    def post(self, request, *args, **kwargs):
        """POST request method handler"""
        form = RequestForm(self.request.POST, prefix="request")
        formset = self.PDFSongFormset(self.request.POST, prefix="songs")
        if form.is_valid() and formset.is_valid():
            request = form.instance
            request.type = RequestType.MANUAL
            with transaction.atomic():
                request.save()
                for form in formset:
                    form.instance.request = request
                    form.instance.save()
            messages.success(self.request,
                             _("PDF Request with id %(id)s was successfully created") % {'id': request.id})
            return self.form_valid()
        return self.form_invalid(form, formset)

    def form_valid(self):
        """If the form is valid, redirect to the supplied URL."""
        return HttpResponseRedirect(str(self.success_url))

    def form_invalid(self, form, formset):
        """If the form is invalid, render the invalid form."""
        return self.render_to_response({"form": form, "formset": formset})
