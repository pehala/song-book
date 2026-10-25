"""Tests for the PDF forms and formsets."""

import pytest
from django.forms import formset_factory
from django.http import QueryDict
from django.test import RequestFactory

from pdf.forms import BasePDFSongFormset, PDFSongForm, SongSelectionForm

pytestmark = pytest.mark.django_db

Formset = formset_factory(PDFSongForm, formset=BasePDFSongFormset, min_num=1, validate_min=True, extra=0)


@pytest.fixture
def tenant_request(tenant):
    """A request whose tenant is set, as the middleware would."""
    request = RequestFactory().get("/")
    request.tenant = tenant
    return request


def formset_data(*pairs):
    """Returns the POST data of the songs formset for (song, number) pairs."""
    data = {
        "songs-TOTAL_FORMS": str(len(pairs)),
        "songs-INITIAL_FORMS": "0",
        "songs-MIN_NUM_FORMS": "1",
        "songs-MAX_NUM_FORMS": "1000",
    }
    for index, (song, number) in enumerate(pairs):
        data[f"songs-{index}-song"] = str(song.pk)
        data[f"songs-{index}-song_number"] = str(number)
    return data


def test_selection_is_limited_to_the_tenant(tenant_request, song, other_category, make_song):
    """Songs of another tenant cannot be picked."""
    foreign = make_song(other_category, name="Foreign Song")
    form = SongSelectionForm(request=tenant_request)

    assert song in form.queryset
    assert foreign not in form.queryset


def test_selection_accepts_songs(tenant_request, song):
    """A selection with at least one song is valid."""
    form = SongSelectionForm(QueryDict(f"songs={song.pk}"), request=tenant_request)

    assert form.is_valid()


def test_selection_rejects_an_empty_choice(tenant_request, song):
    """A template has to print something, and says so in its own words."""
    form = SongSelectionForm(QueryDict(""), request=tenant_request)

    assert not form.is_valid()
    assert form.errors.as_data()["__all__"][0].code == "no_songs"


def test_selection_rejects_an_unknown_song(tenant_request, song):
    """A submitted value that is not a song of this tenant is refused."""
    form = SongSelectionForm(QueryDict("songs=999999"), request=tenant_request)

    assert not form.is_valid()


def test_initial_values_are_read_from_the_initial_data(tenant_request, song):
    """An unbound form reports the songs it was initialised with."""
    form = SongSelectionForm(initial={"songs": [song.pk]}, request=tenant_request)

    assert form.get_list_field_value("songs", []) == [song.pk]


def test_initial_values_are_read_from_submitted_data(tenant_request, song):
    """A bound form reports the songs that were submitted."""
    form = SongSelectionForm(QueryDict(f"songs={song.pk}"), request=tenant_request)

    assert form.get_list_field_value("songs", []) == [str(song.pk)]


def test_missing_field_falls_back_to_the_default(tenant_request):
    """An unknown field reports the given default."""
    form = SongSelectionForm(initial={}, request=tenant_request)

    assert form.get_list_field_value("songs", ["fallback"]) == ["fallback"]


def test_distinct_song_numbers_are_accepted(tenant_request, song, make_song, category):
    """Every song may hold its own position."""
    second = make_song(category, name="Second Song")

    formset = Formset(formset_data((song, 1), (second, 2)), prefix="songs", form_kwargs={"request": tenant_request})

    assert formset.is_valid()


def test_duplicate_song_numbers_are_refused(tenant_request, song, make_song, category):
    """Two songs cannot share a position."""
    second = make_song(category, name="Second Song")

    formset = Formset(formset_data((song, 1), (second, 1)), prefix="songs", form_kwargs={"request": tenant_request})

    assert not formset.is_valid()


def test_invalid_entries_short_circuit_the_check(tenant_request, song):
    """The uniqueness check is skipped while a form is already broken."""
    formset = Formset(formset_data((song, 0)), prefix="songs", form_kwargs={"request": tenant_request})

    assert not formset.is_valid()


def test_numbering_refuses_a_song_of_another_tenant(tenant_request, song, other_category, make_song):
    """A song outside this tenant cannot be put into its template."""
    foreign = make_song(other_category, name="Foreign Song")

    formset = Formset(formset_data((song, 1), (foreign, 2)), prefix="songs", form_kwargs={"request": tenant_request})

    assert not formset.is_valid()
    assert "song" in formset.forms[1].errors
