"""Tests for the locale helpers used while sorting songs."""

import locale

import pytest

from pdf.locales import changed_locale, lang_to_locale


@pytest.mark.parametrize(
    ("language", "expected"),
    [
        pytest.param("en", "en_US.UTF8", id="english"),
        pytest.param("cs", "cs_CZ.UTF8", id="czech"),
        pytest.param("de", None, id="language the songbook does not speak"),
    ],
)
def test_django_languages_map_to_system_locales(language, expected):
    """Django language codes are translated to system locale names"""
    assert lang_to_locale(language) == expected


def test_locale_is_restored_afterwards():
    """The collation locale is put back when the block ends"""
    before = locale.getlocale(locale.LC_COLLATE)

    with changed_locale(None):
        pass

    assert locale.getlocale(locale.LC_COLLATE) == before


def test_locale_is_restored_after_an_error():
    """The collation locale is put back even when the block raises"""
    before = locale.getlocale(locale.LC_COLLATE)

    with pytest.raises(RuntimeError), changed_locale(None):
        raise RuntimeError("boom")

    assert locale.getlocale(locale.LC_COLLATE) == before
