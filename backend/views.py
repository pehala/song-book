"""Views for backend app"""

import hashlib

from django.conf import settings
from django.http import HttpResponse
from django.urls import reverse, reverse_lazy
from django.utils.cache import get_conditional_response
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import RedirectView, TemplateView

from backend.forms import SongForm
from backend.generic import UniversalCreateView, UniversalDeleteView, UniversalUpdateView
from backend.mixins import LocalAdminRequired, PassRequestToFormMixin, RegenerateViewMixin
from backend.models import Song
from backend.songs import cached_json, songs_to_json, visible_songs
from backend.utils import invalidate_songs_cache, regenerate_pdf, regenerate_prerender
from tenants.utils import tenant_cache_key


class BaseSongListView(TemplateView):
    """Renders the song list page; the songs themselves are fetched by the page from a JSON endpoint"""

    template_name = "songs/index.html"

    def get_title(self):
        """Return title of this song set"""
        return self.request.tenant.display_name

    def get_data_url(self):
        """Return URL of the JSON endpoint the page should fetch"""
        raise NotImplementedError

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data["title"] = self.get_title()
        context_data["data_url"] = self.get_data_url()
        return context_data


class AllSongListView(BaseSongListView):
    """Shows all songs for this specific tenant"""

    def get_title(self):
        return f"{_('All Songs')} | {self.request.tenant.display_name}"

    def get_data_url(self):
        return reverse("chords:all_data")


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


class BaseSongsJsonView(ETagJsonMixin, View):
    """
    Serves a songs JSON list from the cache.

    The cache is consulted before any song is loaded or rendered, so cache hits
    and 304 responses cost a single cache lookup.
    """

    def get_cache_key(self):
        """Returns cache key for this list and user"""
        raise NotImplementedError

    def get_queryset(self):
        """Returns songs to serialize on a cache miss"""
        raise NotImplementedError

    def include_archived(self):
        """Archived songs are only shown to superusers"""
        return self.request.user.is_superuser

    def build(self):
        """Serializes the queryset; called only on a cache miss"""
        return songs_to_json(visible_songs(self.get_queryset(), self.include_archived()))

    def get(self, request, *args, **kwargs):
        return self.etag_response(request, cached_json(self.get_cache_key(), self.build))


class AllSongsJsonView(BaseSongsJsonView):
    """Returns songs JSON for /all, served from Redis cache with ETag support"""

    def get_cache_key(self):
        base = tenant_cache_key(self.request.tenant, f"{settings.SONGS_CACHE_KEY}_ALL")
        return f"{base}_archived" if self.request.user.is_superuser else base

    def get_queryset(self):
        return Song.objects.filter(categories__tenant=self.request.tenant).distinct()


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
