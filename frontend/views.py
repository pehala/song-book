"""Views of the reader: the shell, the service worker and the web app manifest"""

import hashlib
import json
from pathlib import Path

from django.conf import settings
from django.contrib.staticfiles import finders
from django.http import HttpResponse, JsonResponse
from django.template.loader import render_to_string
from django.templatetags.static import static
from django.urls import reverse
from django.utils.cache import add_never_cache_headers, get_conditional_response
from django.views import View
from django.views.generic import TemplateView

from tenants.bootstrap import bootstrap_payload

# The reader's modules, the entry point first, and its stylesheet. The shell preloads the modules and the
# service worker stores all of them when it installs, so the reader works offline from the first reload.
ENTRY = "app/app.js"
MODULES = [
    ENTRY,
    "app/chrome.js",
    "app/i18n.js",
    "app/options.js",
    "app/songs.js",
    "app/store.js",
    "app/vendor/preact-htm.module.js",
    "app/vendor/qr.mjs",
]
# Draws the header on the pages the server renders
SITE_ENTRY = "app/site.js"
STYLESHEETS = ["app/header.css", "app/app.css"]
ASSETS = [*MODULES, SITE_ENTRY, *STYLESHEETS]

SHELL_URL = "/"
THEME_COLOR = "#7793f3"
BACKGROUND_COLOR = "#f9f9f9"


def modules_digest(urls):
    """Short digest of what the reader consists of: the hashed urls, and in development the files themselves"""
    digest = hashlib.blake2b(json.dumps(urls).encode(), digest_size=6)
    if settings.DEBUG:  # static files are not hashed in development, so their urls never change
        for path in ASSETS:
            digest.update(Path(finders.find(path)).read_bytes())
    return digest.hexdigest()


def asset_urls():
    """Urls of the static files the reader consists of"""
    return [static(path) for path in ASSETS]


class ShellView(View):
    """
    The page every reader route is served with.

    It holds nothing that depends on the user, the session or the language, so it is cached by the
    service worker and by ETag; the client draws the route from the bootstrap and the songs.
    """

    def get(self, request, slug=None):
        """Renders the shell; a slug that is no category of the tenant gets the same page with status 404"""
        tenant = request.tenant
        body = render_to_string(
            "shell.html",
            {
                "boot": bootstrap_payload(tenant),
                "modules": [static(path) for path in MODULES],
                "entry": static(ENTRY),
                "stylesheets": [static(path) for path in STYLESHEETS],
            },
        )
        known = slug is None or tenant.category_set.filter(slug=slug).exists()
        response = HttpResponse(body, status=200 if known else 404)
        etag = f'"{hashlib.blake2b(body.encode(), digest_size=16).hexdigest()}"'
        response["ETag"] = etag
        response["Cache-Control"] = "no-cache"
        return get_conditional_response(request, etag=etag, response=response)


class ServiceWorkerView(TemplateView):
    """
    The reader's service worker.

    The precached urls are content-hashed, so a changed file changes the worker's bytes and the browser
    installs the new worker; the tenant is part of the cache name for hostnames that change tenant.
    """

    template_name = "sw.js"
    content_type = "application/javascript"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        urls = asset_urls()
        tenant = self.request.tenant
        context["cache_name"] = f"shell-{tenant.id}-{modules_digest(urls)}"
        context["precache"] = json.dumps(urls)
        context["shell_url"] = SHELL_URL
        context["static_url"] = settings.STATIC_URL
        context["runtime"] = json.dumps([reverse("frontend:manifest"), *([tenant.icon.url] if tenant.icon else [])])
        return context

    def render_to_response(self, context, **response_kwargs):
        response = super().render_to_response(context, **response_kwargs)
        add_never_cache_headers(response)
        return response


class ManifestView(TemplateView):
    """The web app manifest of the tenant"""

    def get(self, request, *args, **kwargs):
        tenant = request.tenant
        manifest = {
            "name": tenant.display_name,
            "short_name": tenant.display_name,
            "start_url": SHELL_URL,
            "scope": "/",
            "display": "standalone",
            "theme_color": THEME_COLOR,
            "background_color": BACKGROUND_COLOR,
        }
        if tenant.icon:
            try:
                sizes = f"{tenant.icon.width}x{tenant.icon.height}"
            except FileNotFoundError:
                sizes = None  # the logo was removed from the storage; the manifest is still valid without it
            if sizes:
                manifest["icons"] = [{"src": tenant.icon.url, "sizes": sizes, "type": "image/png"}]
        response = JsonResponse(manifest, content_type="application/manifest+json")
        add_never_cache_headers(response)
        return response
