"""Tests for the reader's gettext catalogue, which travels in the bootstrap."""

import subprocess

import pytest

from frontend.catalogues import reader_catalogues


@pytest.fixture
def empty_locale_dir(tmp_path, settings):
    """An empty locale directory the catalogues are read from, with their cache dropped before and after."""
    settings.LOCALE_PATHS = [str(tmp_path)]
    reader_catalogues.cache_clear()
    yield tmp_path
    reader_catalogues.cache_clear()


@pytest.fixture
def locale_dir(empty_locale_dir):
    """A locale directory with a compiled `djangojs` catalogue of one Czech string."""
    messages = empty_locale_dir / "cs" / "LC_MESSAGES"
    messages.mkdir(parents=True)
    source = messages / "djangojs.po"
    source.write_text(
        'msgid ""\nmsgstr ""\n"Content-Type: text/plain; charset=UTF-8\\n"\n\nmsgid "Close"\nmsgstr "Zavřít"\n'
    )
    subprocess.run(["msgfmt", "-o", str(messages / "djangojs.mo"), str(source)], check=True)
    return empty_locale_dir


def test_translated_languages_map_msgids_to_translations(locale_dir):
    """The reader looks the English text up in the catalogue of its language."""
    assert reader_catalogues() == {"cs": {"Close": "Zavřít"}}


def test_language_without_translations_does_not_borrow_the_default(locale_dir, settings):
    """Django falls back to Czech for other languages; the reader would show Czech in a German page."""
    settings.LANGUAGES = (("en", "English"), ("cs", "Česky"), ("de", "Deutsch"))
    reader_catalogues.cache_clear()

    assert list(reader_catalogues()) == ["cs"]


@pytest.mark.usefixtures("empty_locale_dir")
def test_missing_catalogue_is_left_out():
    """A language that has nothing compiled adds no entry."""
    assert reader_catalogues() == {}


def test_catalogue_is_read_once(locale_dir):
    """The same object is handed out every time."""
    assert reader_catalogues() is reader_catalogues()
