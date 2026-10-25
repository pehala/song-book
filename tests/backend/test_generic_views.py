"""Tests for the generic CRUD view helpers."""

from django.utils import translation

from backend.generic import UniversalCreateView, UniversalDeleteView, UniversalUpdateView, UniversalView
from backend.models import Song
from tenants.models import Tenant


class Nameless:
    """Object without a name, identified by its primary key."""

    id = 7


def view_for(model):
    """Returns a generic view bound to the model."""
    view = UniversalView()
    view.model = model
    return view


def test_verbose_name_comes_from_the_model():
    """The model's own verbose name is used in messages."""
    with translation.override("en"):
        assert str(view_for(Song).get_verbose_name()) == "Song"


def test_identifier_prefers_the_name():
    """Named objects are identified by their name."""
    assert view_for(Song).get_object_identifier(Song(name="Song")) == "Song"


def test_identifier_falls_back_to_the_id():
    """Objects without a name are identified by their id."""
    assert view_for(Nameless).get_object_identifier(Nameless()) == 7


def test_czech_messages_do_not_depend_on_the_gender_of_the_model():
    """The messages name the model first, so they read right for feminine and masculine models alike."""
    with translation.override("cs"):
        for model, name in ((Song, "Písnička"), (Tenant, "Zpěvník")):
            values = {"class": view_for(model).get_verbose_name(), "identifier": "X"}
            assert UniversalDeleteView.success_message % values == f"Úspěšně smazáno: {name} X"
            assert UniversalUpdateView.success_message % values == f"Úspěšně upraveno: {name} X"
            assert UniversalUpdateView.title_message % values == f"Úprava: {name} X"
            assert UniversalCreateView.success_message % values == f"Úspěšně vytvořeno: {name} X"
            assert UniversalCreateView.title_message % values == f"Vytvořit: {name}"
