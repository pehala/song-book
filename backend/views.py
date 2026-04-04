"""Views for backend app"""

import hashlib
import json

from django.conf import settings
from django.core.cache import cache
from django.core.serializers.json import DjangoJSONEncoder
from django.forms import model_to_dict
from django.http import HttpResponse
from django.urls import reverse_lazy, reverse
from django.utils.cache import get_conditional_response
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView, RedirectView

from backend.forms import SongForm
from backend.mixins import RegenerateViewMixin, PassRequestToFormMixin, LocalAdminRequired
from backend.models import Song
from backend.utils import regenerate_pdf, regenerate_prerender, invalidate_songs_cache
from backend.generic import UniversalDeleteView, UniversalUpdateView, UniversalCreateView
from tenants.utils import tenant_cache_key


def transform_song(song: Song, number: int) -> dict:
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

    def get_context_data(self, *, object_list=None, **kwargs):
        context_data = super().get_context_data(object_list=object_list, **kwargs)
        context_data["data_url"] = reverse("chords:all_data")
        return context_data


class ETagJsonMixin:
    """Mixin that adds ETag-based client-side caching to a JSON view.

    Uses Django's get_conditional_response to return 304 Not Modified when
    the client's If-None-Match header matches the ETag of the cached content.
    """

    def etag_response(self, request, json_string):
        """Return a JSON response with ETag, or 304 if the client already has it."""
        etag = f'"{hashlib.blake2b(json_string.encode(), digest_size=16).hexdigest()}"'
        response = HttpResponse(json_string, content_type="application/json")
        response["ETag"] = etag
        response["Cache-Control"] = "no-cache"
        return get_conditional_response(request, etag=etag, response=response)


class AllSongsJsonView(ETagJsonMixin, AllSongListView):
    """Returns songs JSON for /all, served from Redis cache with ETag support"""

    def get_cache_key(self):
        base = tenant_cache_key(self.request.tenant, f"{settings.SONGS_CACHE_KEY}_ALL")
        return f"{base}_auth" if self.request.user.is_authenticated else base

    def render_to_response(self, context, **kwargs):
        key = self.get_cache_key()
        cached = cache.get(key)
        if cached is None:
            cached = context["songs"]  # already a JSON string from get_context_data()
            cache.set(key, cached, settings.CACHE_TIMEOUT)
        return self.etag_response(self.request, cached)


class IndexSongListView(RedirectView):
    """Shows first available category"""

    def get_redirect_url(self, *args, **kwargs):
        return self.request.tenant.index_redirect


class SongCreateView(LocalAdminRequired, PassRequestToFormMixin, UniversalCreateView):
    """Creates new song"""

    form_class = SongForm
    model = Song
    success_url = reverse_lazy("backend:index")

    def get_success_url(self):
        regenerate_pdf(self.object)
        regenerate_prerender(self.object)
        invalidate_songs_cache(self.object)
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
            invalidate_songs_cache(self.object)
        return response


class SongDeleteView(LocalAdminRequired, UniversalDeleteView):
    """Removes song"""

    model = Song
    success_url = reverse_lazy("backend:index")

    def post(self, request, *args, **kwargs):
        song = self.get_object()
        regenerate_pdf(song)
        invalidate_songs_cache(song)
        return super().post(request, *args, **kwargs)
