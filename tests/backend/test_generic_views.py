"""Tests for the generic CRUD view helpers."""

from django.utils import translation

from backend.generic import UniversalView
from backend.models import Song


class Nameless:
    """Object without a name, identified by its primary key"""

    id = 7


def view_for(model):
    view = UniversalView()
    view.model = model
    return view


def test_verbose_name_comes_from_the_model():
    """The model's own verbose name is used in messages"""
    with translation.override("en"):
        assert str(view_for(Song).get_verbose_name()) == "Song"


def test_identifier_prefers_the_name():
    """Named objects are identified by their name"""
    assert view_for(Song).get_object_identifier(Song(name="Song")) == "Song"


def test_identifier_falls_back_to_the_id():
    """Objects without a name are identified by their id"""
    assert view_for(Nameless).get_object_identifier(Nameless()) == 7
