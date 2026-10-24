"""Views for backend app"""

import hashlib

from django.http import HttpResponse, JsonResponse
from django.urls import reverse_lazy
from django.utils.cache import get_conditional_response
from django.views import View

from backend.forms import SongForm
from backend.generic import UniversalCreateView, UniversalDeleteView, UniversalUpdateView
from backend.me import me_payload
from backend.mixins import LocalAdminRequired, PassRequestToFormMixin, RegenerateViewMixin
from backend.models import Song
from backend.songs import cached_songs_payload
from backend.utils import regenerate_pdf


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
        response = JsonResponse(me_payload(request))
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
