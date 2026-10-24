"""The reader's strings live in `i18n.js`, outside the gettext catalogue, so only a test keeps the languages in step."""

import re
from pathlib import Path

from django.conf import settings

I18N = Path(settings.BASE_DIR).parent / "frontend" / "static" / "app" / "i18n.js"
KEY = re.compile(r"^        (\w+):", re.MULTILINE)


def keys_of(language):
    source = I18N.read_text()
    block = re.search(rf"^    {language}: {{\n(.*?)^    }},?\n", source, re.MULTILINE | re.DOTALL)
    return KEY.findall(block.group(1))


def test_every_language_has_the_same_keys():
    """A key missing from one dictionary would show up as its raw name"""
    czech, english = keys_of("cs"), keys_of("en")

    assert czech
    assert set(czech) == set(english), set(czech) ^ set(english)


def test_keys_are_unique_per_language():
    """A duplicate key silently replaces the earlier string"""
    for language in ("cs", "en"):
        keys = keys_of(language)
        assert len(keys) == len(set(keys)), language
