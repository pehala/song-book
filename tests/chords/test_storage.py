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
def test_collectstatic_hashes_module_import(tmp_path):
    """collectstatic produces an Options.js whose js.cookie import points at the hashed file."""
    storages = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "chords.storage.ManifestStorage"},
    }
    static_root = tmp_path / "static"  # MEDIA_ROOT already points at tmp_path and the two must differ
    with override_settings(STORAGES=storages, STATIC_ROOT=str(static_root)):
        call_command("collectstatic", interactive=False, verbosity=0)
        manifest = json.loads((static_root / "staticfiles.json").read_text())["paths"]
        hashed_options = static_root / manifest["js/Options.js"]
        hashed_cookie = manifest["js/js.cookie.js"].rsplit("/", 1)[-1]
        assert hashed_cookie != "js.cookie.js"
        assert f'from "./{hashed_cookie}"' in hashed_options.read_text()
