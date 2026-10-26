"""Views for backend app."""

import hashlib
from urllib.parse import quote

from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.urls import reverse, reverse_lazy
from django.utils.cache import get_conditional_response
from django.utils.http import url_has_allowed_host_and_scheme, urlencode
from django.utils.translation import gettext_lazy as _
from django.views import View
from markdownx.views import ImageUploadView, MarkdownifyView

from analytics.views import ALL_SONGS_KEY, analytics
from backend.forms import SongForm
from backend.generic import UniversalCreateView, UniversalDeleteView, UniversalUpdateView
from backend.me import me_payload
from backend.mixins import LocalAdminRequired, PassRequestToFormMixin, RegenerateViewMixin
from backend.models import Song
from backend.songs import build_songs_delta, cached_songs_payload
from backend.utils import regenerate_pdf

SIZE_HEADER = "X-Songs-Size"
SAVED_COOKIE = "sb-saved"
SAVED_COOKIE_AGE = 24 * 60 * 60


class ETagJsonMixin:
    """Mixin that adds ETag-based client-side caching to a JSON view, with its uncompressed size in `X-Songs-Size`.

    Uses Django's get_conditional_response to return 304 Not Modified when
    the client's If-None-Match header matches the ETag of the cached content.
    """

    def json_response(self, json_string):
        """Return a JSON response that tells its uncompressed size."""
        response = HttpResponse(json_string, content_type="application/json")
        response[SIZE_HEADER] = len(response.content)
        return response

    def etag_response(self, request, json_string, private=False):
        """Return a JSON response with ETag, or 304 if the client already has it; private ones skip shared caches."""
        etag = f'"{hashlib.blake2b(json_string.encode(), digest_size=16).hexdigest()}"'
        response = self.json_response(json_string)
        response["ETag"] = etag
        response["Cache-Control"] = "private, no-cache" if private else "no-cache"
        return get_conditional_response(request, etag=etag, response=response)


class SongsApiView(ETagJsonMixin, View):
    """Serves every song of the tenant with the slugs of its categories, so the browser can filter by category itself.

    Superusers get the variant with archived songs, which only they may cache.
    """

    def get(self, request, *args, **kwargs):
        """Serves the whole list of songs, or the changes since `since` when the stored copy is not current."""
        analytics(request, ALL_SONGS_KEY)
        include_archived = request.user.is_superuser
        payload = cached_songs_payload(request.tenant, include_archived)
        response = self.etag_response(request, payload, private=include_archived)
        since = request.GET.get("since", "")
        if response.status_code == 304 or not since.isdecimal() or len(since) > 10:
            return response
        delta = self.json_response(build_songs_delta(request.tenant, include_archived, int(since), response["ETag"]))
        delta["Cache-Control"] = "private, no-store" if include_archived else "no-store"
        return delta


class MeView(View):
    """Describes the signed in user to the reader, which cannot know it from the cached shell.

    Pending messages are handed over here, since the shell has no place to render them.
    """

    def get(self, request, *args, **kwargs):
        """Returns the state of the user, which is never cached."""
        response = JsonResponse(me_payload(request))
        response["Cache-Control"] = "private, no-store"
        return response


class SongEditorMixin:
    """Renders the song editor, which can also save a song and stay on its page."""

    template_name = "backend/song_form.html"

    def form_valid(self, form):
        """Tells the browser which editor page the server saved, so that it drops the draft of that page."""
        response = super().form_valid(form)
        response.set_cookie(SAVED_COOKIE, quote(self.request.path, safe=""), max_age=SAVED_COOKIE_AGE, samesite="Lax")
        return response

    def get_context_data(self, **kwargs):
        """Adds the address the Cancel button leads back to: where the author came from, or the reader."""
        ctx = super().get_context_data(**kwargs)
        back = self.request.GET.get("next", "")
        if not url_has_allowed_host_and_scheme(back, allowed_hosts={self.request.get_host()}):
            back = str(self.success_url)
        ctx["cancel_url"] = back
        return ctx

    def get_success_url(self):
        """Returns to the editor of the saved song when asked to keep editing."""
        if "continue" not in self.request.POST:
            return super().get_success_url()
        url = reverse("backend:edit", kwargs={"pk": self.object.pk})
        if "next" in self.request.GET:
            url += "?" + urlencode({"next": self.request.GET["next"]})
        return url


class SongCreateView(LocalAdminRequired, PassRequestToFormMixin, SongEditorMixin, UniversalCreateView):
    """Creates new song."""

    form_class = SongForm
    model = Song
    success_url = reverse_lazy("backend:index")
    title_message = _("New song")

    def get_success_url(self):
        """Schedules the PDF regeneration for the new song's categories."""
        regenerate_pdf(self.object)
        return super().get_success_url()


class TenantSongsMixin:
    """Limits the songs a view can reach to those in a category of the current Tenant."""

    def get_queryset(self):
        """Returns the songs in a category of the current Tenant."""
        return super().get_queryset().filter(categories__tenant=self.request.tenant).distinct()


class SongUpdateView(
    LocalAdminRequired,
    TenantSongsMixin,
    PassRequestToFormMixin,
    RegenerateViewMixin,
    SongEditorMixin,
    UniversalUpdateView,
):
    """Updates existing song."""

    form_class = SongForm
    model = Song
    success_url = reverse_lazy("backend:index")
    title_message = _("Editing %(identifier)s")

    def post(self, request, *args, **kwargs):
        """Saves the song and schedules the PDF regeneration for its categories when it changed."""
        response = super().post(request, *args, **kwargs)
        if self.regenerate:
            regenerate_pdf(self.object)
        return response


class SongDeleteView(LocalAdminRequired, TenantSongsMixin, UniversalDeleteView):
    """Removes song; a song that other Tenants list as well only leaves the categories of the current one."""

    model = Song
    success_url = reverse_lazy("backend:index")

    def post(self, request, *args, **kwargs):
        """Schedules the PDF regeneration for the song's categories before it is deleted."""
        regenerate_pdf(self.get_object())
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        """Deletes the song, or takes it out of this Tenant's categories when another Tenant lists it too."""
        own = self.object.categories.filter(tenant=self.request.tenant)
        if self.object.categories.exclude(tenant=self.request.tenant).exists():
            self.object.categories.remove(*own)
            return HttpResponseRedirect(self.get_success_url())
        return super().form_valid(form)


class SongImageUploadView(LocalAdminRequired, ImageUploadView):
    """Stores an image dropped into the song editor."""


class SongPreviewView(LocalAdminRequired, MarkdownifyView):
    """Renders the preview of the song editor."""
