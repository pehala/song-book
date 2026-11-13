"""Views of the reader: the shell, the service worker and the web app manifest."""

import hashlib
import io
import json
from pathlib import Path

from django.conf import settings
from django.contrib.staticfiles import finders
from django.core.cache import cache
from django.http import Http404, HttpResponse, JsonResponse
from django.template.loader import render_to_string
from django.templatetags.static import static
from django.urls import reverse
from django.utils import translation
from django.utils.cache import add_never_cache_headers, get_conditional_response
from django.utils.translation import gettext
from django.views import View
from django.views.generic import TemplateView
from PIL import Image, ImageColor, ImageOps

from tenants.bootstrap import bootstrap_payload
from tenants.menus import CATEGORIES_MENU
from tenants.utils import tenant_cache_key

# The reader's modules, the entry point first, and its stylesheet. The shell preloads the modules and the
# service worker stores all of them when it installs, so the reader works offline from the first reload.
ENTRY = "app/app.js"
MODULES = [
    ENTRY,
    "app/header.js",
    "app/i18n.js",
    "app/options.js",
    "app/songs.js",
    "app/store.js",
    "app/vendor/preact-htm.module.js",
    "app/vendor/qr.mjs",
]
# Draws the header on the pages the server renders
SITE_ENTRY = "app/site.js"
# Draw the content of some of the pages the server renders, through what page.js shares
PAGE_ENTRIES = ["app/progress.js", "app/analytics.js"]
PAGE_MODULES = ["app/page.js", *PAGE_ENTRIES]
STYLESHEETS = ["app/header.css", "app/song.css", "app/app.css"]
ASSETS = [*MODULES, SITE_ENTRY, *PAGE_MODULES, *STYLESHEETS]

SHELL_URL = "/"
THEME_COLOR = "#7793f3"
BACKGROUND_COLOR = "#f9f9f9"

# The square sizes of the app icons drawn from the logo: browsers want at least 192px to install an app, 512px for
# its splash screen
ICON_SIZES = (192, 512)
# A maskable icon is cut to the shape of the platform, which keeps a circle of 80% of the width; a square logo fits
# that circle at 56%
MASKABLE_CONTENT = 0.56
ICON_TIMEOUT = 60 * 60 * 24 * 7


def modules_digest(urls):
    """Short digest of what the reader consists of: the hashed urls, and in development the files themselves."""
    digest = hashlib.blake2b(json.dumps(urls).encode(), digest_size=6)
    if settings.DEBUG:  # static files are not hashed in development, so their urls never change
        for path in ASSETS:
            digest.update(Path(finders.find(path)).read_bytes())
    return digest.hexdigest()


def asset_urls():
    """Urls of the static files the reader consists of."""
    return [static(path) for path in ASSETS]


class ShellView(View):
    """The page every reader route is served with.

    It holds nothing that depends on the user, the session or the language, so it is cached by the
    service worker and by ETag; the client draws the route from the bootstrap and the songs.
    """

    def get(self, request, slug=None):
        """Renders the shell; a slug that is no category of the tenant gets the same page with status 404."""
        tenant = request.tenant
        # In the language of the page, whatever the user's language is: the body is the same for everyone
        with translation.override(settings.LANGUAGE_CODE):
            description = gettext("Songbook %(name)s: lyrics with chords that work offline") % {
                "name": tenant.display_name
            }
        body = render_to_string(
            "shell.html",
            {
                "boot": bootstrap_payload(tenant),
                "description": description,
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
    """The reader's service worker.

    The precached urls are content-hashed, so a changed file changes the worker's bytes and the browser
    installs the new worker; the tenant is part of the cache name for hostnames that change tenant.
    """

    template_name = "service_worker.js"
    content_type = "application/javascript"

    def get_context_data(self, **kwargs):
        """Adds the name of the cache and the urls to precache."""
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
        """Marks the response as uncacheable."""
        response = super().render_to_response(context, **response_kwargs)
        add_never_cache_headers(response)
        return response


def logo_version(tenant):
    """Returns a short digest that changes with the tenant's logo, or None when there is no logo in the storage."""
    if not tenant.icon:
        return None
    try:
        size = tenant.icon.size
    except FileNotFoundError:
        return None  # the logo was removed from the storage
    return hashlib.blake2b(f"{tenant.icon.name}:{size}".encode(), digest_size=6).hexdigest()


def draw_icon(logo, size, maskable):
    """Returns the PNG bytes of a square icon of the given size with the logo (a stored file) fitted in its middle.

    A maskable icon has the background colour of the app around a smaller logo, so that the platform's mask leaves
    all of it; the other is transparent around a logo as large as fits.
    """
    with logo.open("rb") as file, Image.open(file) as source:
        content = round(size * MASKABLE_CONTENT) if maskable else size
        fitted = ImageOps.contain(source.convert("RGBA"), (content, content), Image.Resampling.LANCZOS)
    background = (*ImageColor.getrgb(BACKGROUND_COLOR), 255) if maskable else (0, 0, 0, 0)
    canvas = Image.new("RGBA", (size, size), background)
    canvas.alpha_composite(fitted, ((size - fitted.width) // 2, (size - fitted.height) // 2))
    buffer = io.BytesIO()
    canvas.save(buffer, "PNG", optimize=True)
    return buffer.getvalue()


def manifest_icons(tenant):
    """Returns the manifest's icons drawn from the tenant's logo, or an empty list when it has none."""
    version = logo_version(tenant)
    if version is None:
        return []
    icons = []
    for size in ICON_SIZES:
        for maskable in (False, True):
            name = "frontend:icon_maskable" if maskable else "frontend:icon"
            icons.append(
                {
                    "src": f"{reverse(name, kwargs={'size': size})}?v={version}",
                    "sizes": f"{size}x{size}",
                    "type": "image/png",
                    "purpose": "maskable" if maskable else "any",
                }
            )
    return icons


def manifest_shortcuts(tenant):
    """Returns the shortcuts of the installed app: all songs when the tenant shows them, then every category."""
    shortcuts = [{"name": gettext("All songs"), "url": reverse("backend:all")}] if tenant.all_songs_category else []
    categories = reverse("category:list")
    return shortcuts + [
        {"name": category["name"], "url": f"{categories}{category['slug']}"}
        for category in CATEGORIES_MENU.children_of(tenant)
    ]


class ManifestView(TemplateView):
    """The web app manifest of the tenant."""

    def get(self, request, *args, **kwargs):
        """Returns the manifest, with icons drawn from the logo of the tenant when there is one."""
        tenant = request.tenant
        manifest = {
            "id": SHELL_URL,
            "name": tenant.display_name,
            "short_name": tenant.display_name,
            "start_url": SHELL_URL,
            "scope": "/",
            "display": "standalone",
            "theme_color": THEME_COLOR,
            "background_color": BACKGROUND_COLOR,
            "shortcuts": manifest_shortcuts(tenant),
        }
        if icons := manifest_icons(tenant):
            manifest["icons"] = icons
        response = JsonResponse(manifest, content_type="application/manifest+json")
        add_never_cache_headers(response)
        return response


class IconView(View):
    """An app icon of the tenant, drawn from its logo in one of the sizes the manifest lists."""

    maskable = False

    def get(self, request, size):
        """Returns the icon as a PNG, kept in the cache per logo; the manifest's url changes with the logo.

        A logo Pillow cannot read gives no icon rather than an error.
        """
        tenant = request.tenant
        version = logo_version(tenant)
        if size not in ICON_SIZES or version is None:
            raise Http404
        key = tenant_cache_key(tenant, f"ICON-{size}-{'maskable' if self.maskable else 'any'}-{version}")
        try:
            body = cache.get_or_set(key, lambda: draw_icon(tenant.icon, size, self.maskable), timeout=ICON_TIMEOUT)
        except OSError as error:  # Pillow cannot read the stored logo
            raise Http404 from error
        response = HttpResponse(body, content_type="image/png")
        response["Cache-Control"] = "public, max-age=31536000, immutable"
        return response
