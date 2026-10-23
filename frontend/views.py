"""Views of the reader: the service worker and the web app manifest"""

import hashlib
import json

from django.conf import settings
from django.http import JsonResponse
from django.templatetags.static import static
from django.urls import reverse
from django.utils.cache import add_never_cache_headers
from django.views.generic import TemplateView

# Static files the service worker stores when it installs, so the reader works offline from the first reload
PRECACHE = ["app/vendor/preact-htm.module.js"]

SHELL_URL = "/"
THEME_COLOR = "#7793f3"
BACKGROUND_COLOR = "#f9f9f9"


def precache_urls():
    """Urls of the static files the reader consists of"""
    return [static(path) for path in PRECACHE]


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
        urls = precache_urls()
        tenant = self.request.tenant
        digest = hashlib.blake2b(json.dumps(urls).encode(), digest_size=6).hexdigest()
        context["cache_name"] = f"shell-{tenant.id}-{digest}"
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
            manifest["icons"] = [
                {"src": tenant.icon.url, "sizes": f"{tenant.icon.width}x{tenant.icon.height}", "type": "image/png"}
            ]
        response = JsonResponse(manifest, content_type="application/manifest+json")
        add_never_cache_headers(response)
        return response
