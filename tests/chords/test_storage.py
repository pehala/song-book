"""Tests for the content-hashed static files storage used in production."""

import json

import pytest
from django.core.management import call_command
from django.test import override_settings
from django.urls import reverse

from chords.storage import ManifestStorage

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "chords.storage.ManifestStorage"},
}


def test_module_imports_are_rewritten():
    """The production storage rewrites ES module imports so hashed modules reference hashed modules."""
    assert ManifestStorage.support_js_module_import_aggregation is True


@pytest.mark.django_db
def test_collectstatic_hashes_module_imports(tmp_path):
    """Collectstatic produces modules whose imports point at hashed files."""
    static_root = tmp_path / "static"  # MEDIA_ROOT already points at tmp_path and the two must differ
    with override_settings(STORAGES=STORAGES, STATIC_ROOT=str(static_root)):
        call_command("collectstatic", interactive=False, verbosity=0)
        manifest = json.loads((static_root / "staticfiles.json").read_text())["paths"]
        hashed_app = (static_root / manifest["app/app.js"]).read_text()
        hashed_chrome = (static_root / manifest["app/header.js"]).read_text()
        hashed_songs = manifest["app/songs.js"].rsplit("/", 1)[-1]
        hashed_qr = manifest["app/vendor/qr.mjs"].rsplit("/", 1)[-1]
        hashed_vendor = manifest["app/vendor/preact-htm.module.js"].rsplit("/", 1)[-1]
        assert hashed_songs != "songs.js"
        assert f'from "./{hashed_songs}"' in hashed_app
        assert f'from "./vendor/{hashed_vendor}"' in hashed_app
        assert f'from "./vendor/{hashed_qr}"' in hashed_chrome


@pytest.mark.django_db
def test_song_editor_page_links_hashed_files(tmp_path, staff_client):
    """The files of the song editor have their content in their url, so a changed one is fetched again."""
    with override_settings(STORAGES=STORAGES, STATIC_ROOT=str(tmp_path / "static")):
        call_command("collectstatic", interactive=False, verbosity=0)
        manifest = json.loads((tmp_path / "static/staticfiles.json").read_text())["paths"]
        html = staff_client.get(reverse("backend:add")).content.decode()

    for name in ("app/song.css", "backend/editor.css", "backend/editor.js"):
        assert manifest[name] != name
        assert f"/static/{manifest[name]}" in html
