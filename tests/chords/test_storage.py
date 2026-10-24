"""Tests for the content-hashed static files storage used in production."""

import json

import pytest
from django.core.management import call_command
from django.test import override_settings

from chords.storage import ManifestStorage


def test_module_imports_are_rewritten():
    """The production storage rewrites ES module imports so hashed modules reference hashed modules."""
    assert ManifestStorage.support_js_module_import_aggregation is True


@pytest.mark.django_db
def test_collectstatic_hashes_module_imports(tmp_path):
    """collectstatic produces modules whose imports point at hashed files."""
    storages = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "chords.storage.ManifestStorage"},
    }
    static_root = tmp_path / "static"  # MEDIA_ROOT already points at tmp_path and the two must differ
    with override_settings(STORAGES=storages, STATIC_ROOT=str(static_root)):
        call_command("collectstatic", interactive=False, verbosity=0)
        manifest = json.loads((static_root / "staticfiles.json").read_text())["paths"]
        hashed_app = (static_root / manifest["app/app.js"]).read_text()
        hashed_chrome = (static_root / manifest["app/chrome.js"]).read_text()
        hashed_songs = manifest["app/songs.js"].rsplit("/", 1)[-1]
        hashed_qr = manifest["app/vendor/qr.mjs"].rsplit("/", 1)[-1]
        hashed_vendor = manifest["app/vendor/preact-htm.module.js"].rsplit("/", 1)[-1]
        assert hashed_songs != "songs.js"
        assert f'from "./{hashed_songs}"' in hashed_app
        assert f'from "./vendor/{hashed_vendor}"' in hashed_app
        assert f'from "./vendor/{hashed_qr}"' in hashed_chrome
