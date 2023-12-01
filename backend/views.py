"""Views for backend app"""
import json
from typing import Dict

from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.core.serializers.json import DjangoJSONEncoder
from django.forms import model_to_dict
from django.urls import reverse_lazy, reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, RedirectView

from backend.auth.mixins import RegenerateViewMixin, LocalAdminRequired, PassRequestToFormMixin
from backend.forms import SongForm
from backend.models import Song
from backend.utils import regenerate_pdf, regenerate_prerender


def transform_song(song: Song, number: int, authenticated: bool) -> Dict:
    """Transforms song into a dict representation"""
    transformed = model_to_dict(song, ["id", "name", "capo", "author", "link", "archived"])
    transformed["number"] = number
    if authenticated:
        transformed["edit_url"] = reverse("chords:edit", kwargs={"pk": song.id})
        transformed["delete_url"] = reverse("chords:delete", kwargs={"pk": song.id})
    transformed["text"] = song.rendered_markdown
    return transformed


class SongListView(ListView):
    """Lists songs in the one page application"""

    model = Song
    template_name = "songs/index.html"
    context_object_name = "songs"

    FIELDS = ["id", "name", "capo", "author", "link", "prerendered_web"]

    def get_queryset(self):
        queryset = super().get_queryset()
        if not self.request.user.is_superuser:
            queryset = queryset.filter(archived=False)
        return queryset

    def get_context_data(self, *, object_list=None, **kwargs):
        context_data = super().get_context_data(object_list=object_list, **kwargs)
        authenticated = self.request.user.is_authenticated

        songs = []

        archived = []
        i = 1
        for song in context_data["songs"]:
            if song.archived:
                archived.append(song)
                continue
            songs.append(transform_song(song, i, authenticated))
            i += 1

        for song in archived:
            songs.append(transform_song(song, i, authenticated))
            i += 1

        context_data["songs"] = json.dumps(songs, cls=DjangoJSONEncoder)
        return context_data


class IndexSongListView(RedirectView):
    """Shows first available category"""

    # KEY = gettext_noop("Index Page")

    def get_redirect_url(self, *args, **kwargs):
        """
        Return the URL redirect to. Keyword arguments from the URL pattern
        match generating the redirect request are provided as kwargs to this
        method.
        """
        return self.request.tenant.index_redirect


class SongCreateView(LocalAdminRequired, PassRequestToFormMixin, SuccessMessageMixin, CreateView):
    """Creates new song"""

    form_class = SongForm
    model = Song
    template_name = "songs/add.html"
    success_message = _("Song %(name)s was successfully created")
    success_url = reverse_lazy("backend:index")

    def get_success_url(self):
        regenerate_pdf(self.object)
        regenerate_prerender(self.object)
        return super().get_success_url()


class SongUpdateView(LocalAdminRequired, PassRequestToFormMixin, SuccessMessageMixin, RegenerateViewMixin, UpdateView):
    """Updates existing song"""

    form_class = SongForm
    model = Song
    template_name = "songs/add.html"
    success_url = reverse_lazy("backend:index")
    success_message = _("Song %(name)s was successfully updated")

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if self.regenerate:
            regenerate_pdf(self.object, True)
            regenerate_prerender(self.object)
        return response


class SongDeleteView(LocalAdminRequired, DeleteView):
    """Removes song"""

    model = Song
    template_name = "songs/confirm_delete.html"
    success_url = reverse_lazy("backend:index")
    success_message = _("Song %s was successfully deleted")

    def post(self, request, *args, **kwargs):
        regenerate_pdf(self.get_object())
        response = super().post(request, *args, **kwargs)
        messages.success(self.request, self.success_message % self.object.name)
        return response


#
# @method_decorator(login_required, name="dispatch")
# class SongsDatatableView(BaseDatatableView):
#     """API for datatables that returns all songs"""
#
#     model = Song
#     max_display_length = 500
#     columns = ["name", "author", "capo"]
