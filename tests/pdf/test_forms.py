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


@pytest.mark.parametrize("sections", ["", "category"])
def test_sections_may_be_none_or_by_category(tenant_request, song, sections):
    """Both ways of starting the sections are accepted, and none is the default."""
    form = SongSelectionForm(QueryDict(f"songs={song.pk}&sections={sections}"), request=tenant_request)

    assert form.is_valid()
    assert form.cleaned_data["sections"] == sections


def test_sections_are_optional(tenant_request, song):
    """A form without the choice starts without sections."""
    form = SongSelectionForm(QueryDict(f"songs={song.pk}"), request=tenant_request)

    assert form.is_valid()
    assert form.cleaned_data["sections"] == ""


def test_other_sections_are_refused(tenant_request, song):
    """Only the offered choices are accepted."""
    form = SongSelectionForm(QueryDict(f"songs={song.pk}&sections=alphabet"), request=tenant_request)

    assert not form.is_valid()


def test_a_song_is_stored_with_its_section(tenant_request, song):
    """The section of a row is read from the formset, and an empty one means no section."""
    data = formset_data((song, 1))
    data["songs-0-section"] = "Camp"

    formset = Formset(data, prefix="songs", form_kwargs={"request": tenant_request})

    assert formset.is_valid()
    assert formset.forms[0].cleaned_data["section"] == "Camp"


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


def sectioned_formset(tenant_request, song, make_song, category, *sections):
    """A formset with a song for each of the sections, numbered from 1, the section of a song being its name."""
    songs = [song] + [make_song(category, name=f"Song {index}") for index in range(len(sections) - 1)]
    data = formset_data(*[(song, number) for number, song in enumerate(songs, start=1)])
    for index, section in enumerate(sections):
        data[f"songs-{index}-section"] = section
    return Formset(data, prefix="songs", form_kwargs={"request": tenant_request})


def test_sections_in_one_piece_are_accepted(tenant_request, song, make_song, category):
    """A section may hold several songs, as long as they are together."""
    assert sectioned_formset(tenant_request, song, make_song, category, "Camp", "Camp", "Evening", "").is_valid()


def test_a_section_that_comes_back_is_refused(tenant_request, song, make_song, category):
    """Camp, Evening, Camp would print two Camp sections, so the admin is told which one is split."""
    formset = sectioned_formset(tenant_request, song, make_song, category, "Camp", "Evening", "Camp")

    assert not formset.is_valid()
    assert formset.non_form_errors() == ["Každá sekce musí být vcelku, tyto jsou rozdělené: Camp"]


def test_the_sections_are_checked_in_the_order_of_the_numbers(tenant_request, song, make_song, category):
    """The order of the rows posted does not matter, the numbers do."""
    first, second, third = song, make_song(category, name="Second"), make_song(category, name="Third")
    data = formset_data((third, 1), (first, 3), (second, 2))
    for index, section in enumerate(["Camp", "Camp", "Evening"]):
        data[f"songs-{index}-section"] = section

    assert not Formset(data, prefix="songs", form_kwargs={"request": tenant_request}).is_valid()


def test_songs_without_a_section_after_the_sections_are_split_up(tenant_request, song, make_song, category):
    """Songs without a section that come back after another section are all titled alike, so they are refused too."""
    formset = sectioned_formset(tenant_request, song, make_song, category, "Camp", "", "Evening", "")

    assert not formset.is_valid()
    assert "Ostatní" in formset.non_form_errors()[0]


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
