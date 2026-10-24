"""Tests for the service worker and the web app manifest."""

import json
import posixpath
import re
from pathlib import Path

import pytest
from django.contrib.staticfiles import finders
from django.core.files.uploadedfile import SimpleUploadedFile
from django.templatetags.static import static
from django.test import Client
from django.urls import reverse
from PIL import Image

from frontend.views import ASSETS, ENTRY, MODULES, PAGE_ENTRIES, PAGE_MODULES, SITE_ENTRY, STYLESHEETS

pytestmark = pytest.mark.django_db

SERVICE_WORKER_URL = reverse("frontend:service_worker")
MANIFEST_URL = reverse("frontend:manifest")


def array(source, name):
    """The JSON value a `const NAME = [...];` line of the worker holds"""
    return json.loads(re.search(rf"const {name} = (.*);", source).group(1))


def worker(client):
    return client.get(SERVICE_WORKER_URL).content.decode()


def test_worker_is_javascript_served_from_the_root(anon_client, tenant):
    """The path decides the scope, so it has to be the root"""
    response = anon_client.get(SERVICE_WORKER_URL)

    assert SERVICE_WORKER_URL == "/service_worker.js"
    assert response["Content-Type"].startswith("application/javascript")


def test_worker_is_never_cached(anon_client, tenant):
    """The browser has to see a new worker as soon as there is one"""
    assert "no-cache" in anon_client.get(SERVICE_WORKER_URL)["Cache-Control"]


def test_worker_precaches_the_shell_and_the_static_files(anon_client, tenant):
    """The cached files are the content-hashed urls the pages ask for"""
    source = worker(anon_client)

    assert static("app/vendor/preact-htm.module.js") in array(source, "PRECACHE")
    for path in ("app/app.css", "app/header.css", "app/site.js", "app/header.js"):
        assert static(path) in array(source, "PRECACHE")
    assert 'const SHELL = "/";' in source


def test_cache_name_belongs_to_the_tenant(tenant, other_tenant):
    """A hostname that changes tenant starts from an empty cache"""
    first = re.search(r'CACHE = "(.*)"', worker(Client(HTTP_HOST="localhost"))).group(1)
    second = re.search(r'CACHE = "(.*)"', worker(Client(HTTP_HOST="other.localhost"))).group(1)

    assert first.startswith(f"shell-{tenant.id}-")
    assert second.startswith(f"shell-{other_tenant.id}-")


def test_cache_name_follows_the_precached_urls(anon_client, tenant, settings):
    """New static files mean a new cache, which makes the browser install the new worker"""
    before = re.search(r'CACHE = "(.*)"', worker(anon_client)).group(1)
    settings.STATIC_URL = "/other-static/"

    assert re.search(r'CACHE = "(.*)"', worker(anon_client)).group(1) != before


def test_manifest_is_cached_at_runtime(anon_client, tenant):
    """The manifest is fetched by the browser, not by the page"""
    assert MANIFEST_URL in array(worker(anon_client), "RUNTIME")


def test_logo_is_cached_at_runtime(anon_client, tenant):
    """The logo is the one media file the shell shows"""
    tenant.icon = "uploads/logo.png"
    tenant.save()

    assert tenant.icon.url in array(worker(anon_client), "RUNTIME")


def test_reader_routes_leave_the_category_admin_alone():
    """The worker's route pattern matches the reader and nothing else under /categories"""
    source = (Path(__file__).parents[2] / "frontend/templates/service_worker.js").read_text()
    pattern = re.search(r"const READER = /(.*)/;", source).group(1)
    paths = ["/", "/all", "/categories/cs", "/categories/", "/categories/add", "/categories/move"]
    paths += ["/categories/edit/3", "/add", "/api/songs"]

    assert [path for path in paths if re.search(pattern, path)] == ["/", "/all", "/categories/cs"]


def test_manifest_describes_the_tenant(anon_client, tenant):
    """The installed app is named after the songbook and starts on the shell"""
    response = anon_client.get(MANIFEST_URL)
    manifest = json.loads(response.content)

    assert response["Content-Type"] == "application/manifest+json"
    assert (manifest["name"], manifest["start_url"], manifest["display"]) == (tenant.display_name, "/", "standalone")
    assert "icons" not in manifest


def test_manifest_lists_the_logo(anon_client, tenant, media_root):
    """The uploaded logo is the app icon"""
    buffer = media_root / "logo.png"
    Image.new("RGB", (64, 48)).save(buffer)
    tenant.icon = SimpleUploadedFile("logo.png", buffer.read_bytes(), content_type="image/png")
    tenant.save()

    icons = json.loads(anon_client.get(MANIFEST_URL).content)["icons"]

    assert icons == [{"src": tenant.icon.url, "sizes": "64x48", "type": "image/png"}]


def test_manifest_survives_a_missing_logo_file(anon_client, tenant):
    """A logo that is no longer in the storage costs the icon, not the manifest"""
    tenant.icon = "uploads/gone.png"
    tenant.save()

    manifest = json.loads(anon_client.get(MANIFEST_URL).content)

    assert "icons" not in manifest


def test_manifest_follows_the_tenant(tenant, other_tenant):
    """Each hostname gets its own app"""
    manifest = json.loads(Client(HTTP_HOST="other.localhost").get(MANIFEST_URL).content)

    assert manifest["name"] == other_tenant.display_name


@pytest.mark.parametrize("path", ASSETS)
def test_every_asset_is_a_static_file(path):
    """The worker precaches and the pages preload what is listed, so a renamed or deleted file must leave the list"""
    assert finders.find(path)


def test_assets_are_the_modules_the_entries_and_the_styles():
    """The list the worker precaches covers everything the pages load"""
    assert [*MODULES, SITE_ENTRY, *PAGE_MODULES, *STYLESHEETS] == ASSETS
    assert MODULES[0] == ENTRY


def test_every_module_is_reachable_from_an_entry():
    """A listed module that nothing imports is dead weight in the precache"""
    root = Path(__file__).parents[2] / "frontend/static"
    sources = {path: (root / path).read_text() for path in ASSETS if path.endswith((".js", ".mjs"))}
    imported = {ENTRY, SITE_ENTRY, *PAGE_ENTRIES}
    pending = [ENTRY, SITE_ENTRY, *PAGE_ENTRIES]
    while pending:
        current = pending.pop()
        for relative in re.findall(r'from "(\.[^"]+)"', sources[current]):
            target = posixpath.normpath(posixpath.join(posixpath.dirname(current), relative))
            if target not in imported:
                imported.add(target)
                pending.append(target)

    assert set(sources) == imported


@pytest.fixture
def development_files(tmp_path, monkeypatch, settings):
    """Development: static files are not hashed, and the stylesheet is a file the test can edit"""
    settings.DEBUG = True
    stylesheet = tmp_path / "header.css"
    stylesheet.write_text("a {}")
    find = finders.find
    monkeypatch.setattr(
        "frontend.views.finders.find", lambda path: stylesheet if path == "app/header.css" else find(path)
    )
    return stylesheet


def cache_name(client):
    return re.search(r'CACHE = "(.*)"', worker(client)).group(1)


def test_worker_is_built_in_development(anon_client, tenant, development_files):
    """The worker is served while static files are not hashed"""
    assert anon_client.get(SERVICE_WORKER_URL).status_code == 200


def test_worker_version_follows_file_content_in_development(anon_client, tenant, development_files):
    """Edited files change the worker, since their urls do not change"""
    before = cache_name(anon_client)

    development_files.write_text("a { color: red }")

    assert cache_name(anon_client) != before


def test_worker_version_is_stable_while_nothing_changes(anon_client, tenant, development_files):
    """The browser does not install a worker per request"""
    assert cache_name(anon_client) == cache_name(anon_client)
