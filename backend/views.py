"""Views for backend app"""

import json
from typing import Dict

from django.core.serializers.json import DjangoJSONEncoder
from django.forms import model_to_dict
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView, RedirectView

from backend.forms import SongForm
from backend.mixins import RegenerateViewMixin, PassRequestToFormMixin, LocalAdminRequired
from backend.models import Song
from backend.utils import regenerate_pdf, regenerate_prerender
from backend.generic import UniversalDeleteView, UniversalUpdateView, UniversalCreateView


def transform_song(song: Song, number: int) -> Dict:
    """Transforms song into a dict representation"""
    transformed = model_to_dict(song, ["id", "name", "capo", "author", "link", "archived"])
    transformed["number"] = number
    transformed["text"] = song.rendered_markdown
    return transformed


class BaseSongListView(ListView):
    """Lists songs in the one page application"""

    model = Song
    template_name = "songs/index.html"
    context_object_name = "songs"

    FIELDS = ["id", "name", "capo", "author", "link", "prerendered"]

    def get_queryset(self):
        queryset = super().get_queryset()
        if not self.request.user.is_superuser:
            queryset = queryset.filter(archived=False)
        return queryset

    def get_title(self):
        """Return title of this song set"""
        return self.request.tenant.display_name

    def get_context_data(self, *, object_list=None, **kwargs):
        context_data = super().get_context_data(object_list=object_list, **kwargs)

        songs = []
        archived = []

        i = 1
        for song in context_data["songs"]:
            if song.archived:
                archived.append(song)
                continue
            songs.append(transform_song(song, i))
            i += 1

        for song in archived:
            songs.append(transform_song(song, i))
            i += 1

        context_data["songs"] = json.dumps(songs, cls=DjangoJSONEncoder)
        context_data["title"] = self.get_title()
        return context_data


class AllSongListView(BaseSongListView):
    """Returns all songs for this specific tenant"""

    def get_queryset(self):
        return super().get_queryset().filter(categories__tenant=self.request.tenant).distinct()

    def get_title(self):
        """Return title of this song set"""
        return f"{_('All Songs')} | {self.request.tenant.display_name}"


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


class SongCreateView(LocalAdminRequired, PassRequestToFormMixin, UniversalCreateView):
    """Creates new song"""

    form_class = SongForm
    model = Song
    success_url = reverse_lazy("backend:index")

    def get_success_url(self):
        regenerate_pdf(self.object)
        regenerate_prerender(self.object)
        return super().get_success_url()


class SongUpdateView(
    LocalAdminRequired,
    PassRequestToFormMixin,
    RegenerateViewMixin,
    UniversalUpdateView,
):
    """Updates existing song"""

    form_class = SongForm
    model = Song
    success_url = reverse_lazy("backend:index")

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if self.regenerate:
            regenerate_pdf(self.object)
            regenerate_prerender(self.object)
        return response


class SongDeleteView(LocalAdminRequired, UniversalDeleteView):
    """Removes song"""

    model = Song
    success_url = reverse_lazy("backend:index")

    def post(self, request, *args, **kwargs):
        regenerate_pdf(self.get_object())
        response = super().post(request, *args, **kwargs)
        return response
