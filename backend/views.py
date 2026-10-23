"""Views for backend app"""

import hashlib

from django.conf import settings
from django.contrib.messages import get_messages
from django.http import HttpResponse, JsonResponse
from django.middleware.csrf import get_token
from django.urls import reverse_lazy
from django.utils.cache import get_conditional_response
from django.views import View

from backend.auth import is_localadmin
from backend.forms import SongForm
from backend.generic import UniversalCreateView, UniversalDeleteView, UniversalUpdateView
from backend.mixins import LocalAdminRequired, PassRequestToFormMixin, RegenerateViewMixin
from backend.models import Song
from backend.songs import cached_json, cached_songs_payload, songs_to_json, visible_songs
from backend.utils import regenerate_pdf
from tenants.utils import tenant_cache_key


class ETagJsonMixin:
    """Mixin that adds ETag-based client-side caching to a JSON view.

    Uses Django's get_conditional_response to return 304 Not Modified when
    the client's If-None-Match header matches the ETag of the cached content.
    """

    def etag_response(self, request, json_string, private=False):
        """Return a JSON response with ETag, or 304 if the client already has it; private ones skip shared caches"""
        etag = f'"{hashlib.blake2b(json_string.encode(), digest_size=16).hexdigest()}"'
        response = HttpResponse(json_string, content_type="application/json")
        response["ETag"] = etag
        response["Cache-Control"] = "private, no-cache" if private else "no-cache"
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


class SongsApiView(ETagJsonMixin, View):
    """
    Serves every song of the tenant with the slugs of its categories, so the browser can filter by category itself.

    Superusers get the variant with archived songs, which only they may cache.
    """

    def get(self, request, *args, **kwargs):
        include_archived = request.user.is_superuser
        payload = cached_songs_payload(request.tenant, include_archived)
        return self.etag_response(request, payload, private=include_archived)


class MeView(View):
    """
    Describes the signed in user to the reader, which cannot know it from the cached shell.

    Pending messages are handed over here, since the shell has no place to render them.
    """

    def get(self, request, *args, **kwargs):
        get_token(request)
        user = request.user
        response = JsonResponse(
            {
                "auth": user.is_authenticated,
                "username": user.get_username() if user.is_authenticated else None,
                "localadmin": is_localadmin(request),
                "superuser": user.is_superuser,
                "messages": [{"level": message.level_tag, "text": str(message)} for message in get_messages(request)],
            }
        )
        response["Cache-Control"] = "private, no-store"
        return response


class SongCreateView(LocalAdminRequired, PassRequestToFormMixin, UniversalCreateView):
    """Creates new song"""

    form_class = SongForm
    model = Song
    success_url = reverse_lazy("backend:index")

    def get_success_url(self):
        regenerate_pdf(self.object)
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
        return response


class SongDeleteView(LocalAdminRequired, UniversalDeleteView):
    """Removes song"""

    model = Song
    success_url = reverse_lazy("backend:index")

    def post(self, request, *args, **kwargs):
        regenerate_pdf(self.get_object())
        return super().post(request, *args, **kwargs)
