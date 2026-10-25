"""Tests for the Category model."""

import pytest

pytestmark = pytest.mark.django_db


def test_str_is_the_name(category):
    """Categories identify themselves by name."""
    assert str(category) == "Test Category"


def test_get_songs_numbers_from_one(category, song):
    """Songs are handed to the PDF renderer with their position."""
    assert category.get_songs() == [(1, song)]


def test_get_songs_skips_archived(category, song, archived_song):
    """Archived songs are never printed."""
    numbered = category.get_songs()

    assert [entry[1] for entry in numbered] == [song]


def test_get_songs_is_empty_without_songs(category):
    """An empty category produces an empty song list."""
    assert category.get_songs() == []
