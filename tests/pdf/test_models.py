"""Tests for the PDF template and file models."""

import json

import pytest
from django.urls import reverse
from django.utils.timezone import now

from pdf.models import Section, Status, group_sections
from pdf.models.request import AllSongsTemplate, PDFFile, PDFSong, upload_path

pytestmark = pytest.mark.django_db


def make_file(tenant, template=None, **kwargs):
    """Creates a PDF file of the tenant, queued unless told otherwise."""
    kwargs.setdefault("filename", "songbook")
    kwargs.setdefault("status", Status.QUEUED)
    kwargs.setdefault("update_date", now())
    return PDFFile.objects.create(tenant=tenant, template=template, **kwargs)


def test_name_falls_back_to_the_filename(tenant):
    """Without a display name the file is named after its filename."""
    assert make_file(tenant).name == "songbook.pdf"


def test_display_name_wins(tenant):
    """A display name replaces the filename entirely."""
    assert make_file(tenant, display_name="Campfire").name == "Campfire"


@pytest.mark.parametrize(
    ("status", "finished"),
    [
        pytest.param(Status.QUEUED, False, id="queued"),
        pytest.param(Status.SCHEDULED, False, id="scheduled"),
        pytest.param(Status.IN_PROGRESS, False, id="in progress"),
        pytest.param(Status.DONE, True, id="done"),
        pytest.param(Status.FAILED, True, id="failed"),
    ],
)
def test_finished_reflects_the_status(tenant, status, finished):
    """Only done and failed files are finished."""
    assert make_file(tenant, status=status).finished is finished


def test_latest_file_is_the_most_recent_one(tenant, category):
    """Templates expose the newest file they produced."""
    make_file(tenant, category, update_date=now())
    newest = make_file(tenant, category, update_date=now())

    assert category.latest_file == newest


def test_latest_file_is_none_without_files(category):
    """A template that never produced anything has no latest file."""
    assert category.latest_file is None


@pytest.mark.parametrize(
    ("status", "scheduled"),
    [
        pytest.param(Status.QUEUED, True, id="queued"),
        pytest.param(Status.SCHEDULED, True, id="scheduled"),
        pytest.param(Status.IN_PROGRESS, True, id="in progress"),
        pytest.param(Status.DONE, False, id="done"),
        pytest.param(Status.FAILED, False, id="failed"),
    ],
)
def test_has_scheduled_file(tenant, category, status, scheduled):
    """A template is busy while its newest file is unfinished."""
    make_file(tenant, category, status=status)

    assert bool(category.has_scheduled_file()) is scheduled


def test_has_no_scheduled_file_without_files(category):
    """A template that never produced anything is not busy."""
    assert not category.has_scheduled_file()


def test_copy_options_takes_over_the_print_settings(category, manual_template):
    """Options are copied between templates without touching identity."""
    manual_template.filename = "other"
    manual_template.title = "Other Title"
    manual_template.margin = 2.5
    manual_template.link = "https://example.test"

    category.copy_options(manual_template)

    assert category.filename == "other"
    assert category.title == "Other Title"
    assert category.margin == 2.5
    assert category.link == "https://example.test"
    assert category.name == "Test Category"


@pytest.mark.parametrize(
    ("link", "url"),
    [
        ("", ""),
        ("jerry.crazycactus.eu", "https://jerry.crazycactus.eu"),
        ("  jerry.crazycactus.eu/songs ", "https://jerry.crazycactus.eu/songs"),
        ("localhost:8000", "https://localhost:8000"),
        ("https://jerry.crazycactus.eu", "https://jerry.crazycactus.eu"),
        ("HTTP://jerry.crazycactus.eu", "HTTP://jerry.crazycactus.eu"),
        ("mailto:jerry@example.test", "mailto:jerry@example.test"),
    ],
)
def test_link_url_adds_the_missing_scheme(category, link, url):
    """A link typed without a scheme gets https://, one that names a scheme is kept."""
    category.link = link

    assert category.link_url == url


def test_manual_template_returns_numbered_songs(manual_template, pdf_song_entry, pdf_song):
    """Manual templates print the songs in the order the user assigned."""
    assert manual_template.get_songs() == [(1, pdf_song)]


def test_a_template_prints_one_untitled_section_by_default(category, song):
    """Templates without sections hand the renderer all their songs as a single section without a title."""
    assert category.get_sections() == [Section(None, [(1, song)])]


def test_the_default_section_is_in_song_number_order(manual_template, pdf_song, make_song):
    """The songs of a section are printed by number, whatever order the template returned them in."""
    PDFSong.objects.create(song=pdf_song, request=manual_template, song_number=2)
    first = make_song(name="First")
    PDFSong.objects.create(song=first, request=manual_template, song_number=1)

    assert manual_template.get_sections() == [Section(None, [(1, first), (2, pdf_song)])]


def test_upload_path_is_namespaced_by_tenant(tenant):
    """Uploaded files are stored per tenant and day."""
    file = make_file(tenant)

    path = upload_path(file, "songbook.pdf")

    assert path.startswith(f"pdfs/{tenant.id}/")
    assert path.endswith("songbook.pdf")


def test_all_songs_template_is_named_after_the_list(all_songs_template):
    """The template is listed under the name of the list it prints."""
    assert all_songs_template.name == "Všechny Písničky"


def test_all_songs_template_numbers_songs_from_one(all_songs_template, song):
    """Songs are handed to the PDF renderer with their position."""
    assert all_songs_template.get_songs() == [(1, song)]


def test_all_songs_template_skips_archived_songs(all_songs_template, song, archived_song):
    """Archived songs are never printed."""
    assert [entry[1] for entry in all_songs_template.get_songs()] == [song]


def test_all_songs_template_lists_a_song_of_two_categories_once(all_songs_template, song, make_category):
    """The numbering follows the all songs list, where every song appears once."""
    song.categories.add(make_category(all_songs_template.tenant, name="Second", slug="second"))

    assert all_songs_template.get_songs() == [(1, song)]


def test_all_songs_template_numbers_like_the_reader(anon_client, all_songs_template, category, make_song):
    """The song numbers are the ones the all songs list shows."""
    make_song(category, name="First")
    make_song(category, name="Second")

    listed = {row["id"]: row["number"] for row in json.loads(anon_client.get(reverse("chords:songs_api")).content)}

    assert {song.pk: number for number, song in all_songs_template.get_songs()} == listed


def test_all_songs_template_is_one_section_without_category_sections(all_songs_template, song):
    """The default is the plain list, numbered like the all songs list."""
    assert all_songs_template.get_sections() == [Section(None, [(1, song)])]


@pytest.fixture
def sectioned(all_songs_template, category, make_category, make_song):
    """The all songs template with sections, over `category` and a second one that shares a song with it."""
    all_songs_template.category_sections = True
    all_songs_template.save()
    second = make_category(all_songs_template.tenant, name="Second", slug="second")
    shared = make_song(category, second, name="Shared")
    return all_songs_template, category, second, shared


def test_all_songs_template_has_a_section_per_category(sectioned, make_song):
    """The sections are titled after the categories, in the order they were made, and numbered one after another."""
    template, category, second, shared = sectioned
    only_first = make_song(category, name="Only first")
    only_second = make_song(second, name="Only second")

    assert template.get_sections() == [
        Section(category.name, [(1, shared), (2, only_first)]),
        Section("Second", [(3, only_second)]),
    ]


def test_all_songs_template_prints_a_song_in_the_first_category_it_is_in(sectioned):
    """A song of several categories is not repeated in the later ones, which would also repeat its number."""
    template, category, _second, shared = sectioned

    sections = template.get_sections()

    assert sections == [Section(category.name, [(1, shared)])]


def test_all_songs_template_skips_empty_sections(sectioned, make_category, make_song):
    """A category without printable songs has no section; neither do archived songs make one."""
    template, category, *_ = sectioned
    make_song(make_category(template.tenant, name="Empty", slug="empty"), archived=True)

    assert [section.title for section in template.get_sections()] == [category.name]


def test_all_songs_template_sections_ignore_other_tenants(sectioned, other_category, make_song):
    """Categories and songs of other tenants are not printed."""
    template, category, *_ = sectioned
    make_song(other_category)

    assert [section.title for section in template.get_sections()] == [category.name]


def test_all_songs_template_sections_keep_the_list_order_in_a_category(sectioned, make_song):
    """Within a category the songs come in the order of its list, which is the order of the reader."""
    template, category, _second, shared = sectioned
    later = make_song(category, name="Later")

    assert template.get_sections()[0].songs == [(1, shared), (2, later)]


def test_group_sections_starts_a_section_where_the_label_changes():
    """A run of one label is a section, and the same label again is a new section."""
    rows = [(1, "a", "One"), (2, "b", "One"), (3, "c", "Two"), (4, "d", "One")]

    assert group_sections(rows) == [
        Section("One", [(1, "a"), (2, "b")]),
        Section("Two", [(3, "c")]),
        Section("One", [(4, "d")]),
    ]


def test_group_sections_leaves_the_first_section_untitled():
    """Songs before the first label need no title."""
    assert group_sections([(1, "a", ""), (2, "b", "One")]) == [Section(None, [(1, "a")]), Section("One", [(2, "b")])]


def test_group_sections_titles_a_later_untitled_section():
    """Songs without a label after a titled section would look like its own, so they get a title."""
    rows = [(1, "a", "One"), (2, "b", ""), (3, "c", "Two"), (4, "d", "")]

    assert group_sections(rows) == [
        Section("One", [(1, "a")]),
        Section("Ostatní", [(2, "b")]),
        Section("Two", [(3, "c")]),
        Section("Ostatní", [(4, "d")]),
    ]


def test_group_sections_of_nothing_is_empty():
    """No songs, no sections."""
    assert group_sections([]) == []


def test_all_songs_template_ignores_other_tenants(all_songs_template, other_category, make_song):
    """Songs of other tenants are not printed."""
    make_song(other_category)

    assert all_songs_template.get_songs() == []


def test_for_tenant_creates_the_template_once(tenant):
    """The first call creates the template with the defaults, later calls return it."""
    created = AllSongsTemplate.for_tenant(tenant, filename="first", locale="en")

    assert AllSongsTemplate.for_tenant(tenant, filename="second", locale="cs") == created
    assert created.filename == "first"
    assert not created.generate_pdf
