"""Tests for the PDF template and file models."""

import json
from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils.timezone import now

from pdf.models import Section, Status, group_sections
from pdf.models.request import AllSongsTemplate, PDFSong, category_rows, upload_path

pytestmark = pytest.mark.django_db


def test_name_falls_back_to_the_filename(make_pdf_file):
    """Without a display name the file is named after its filename."""
    assert make_pdf_file().name == "songbook.pdf"


def test_display_name_wins(make_pdf_file):
    """A display name replaces the filename entirely."""
    assert make_pdf_file(display_name="Campfire").name == "Campfire"


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
def test_finished_reflects_the_status(make_pdf_file, status, finished):
    """Only done and failed files are finished."""
    assert make_pdf_file(status=status).finished is finished


def test_latest_file_is_the_most_recent_one(category, make_pdf_file):
    """Templates expose the newest file they produced."""
    make_pdf_file(category)
    newest = make_pdf_file(category)

    assert category.latest_file == newest


def test_latest_file_is_none_without_files(category):
    """A template that never produced anything has no latest file."""
    assert category.latest_file is None


def test_latest_generated_file_skips_files_still_waiting(category, make_pdf_file):
    """A file queued after a finished one does not hide the finished one."""
    done = make_pdf_file(category, status=Status.DONE, file="songbook.pdf", update_date=now() - timedelta(days=1))
    make_pdf_file(category, status=Status.SCHEDULED)

    assert category.latest_generated_file == done
    assert category.latest_file.status == Status.SCHEDULED


def test_latest_generated_file_is_none_without_a_finished_file(category, make_pdf_file):
    """Failed and waiting files are not generated files."""
    make_pdf_file(category, status=Status.FAILED)
    make_pdf_file(category, status=Status.QUEUED)

    assert category.latest_generated_file is None


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
def test_has_scheduled_file(category, make_pdf_file, status, scheduled):
    """A template is busy while its newest file is unfinished."""
    make_pdf_file(category, status=status)

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


def test_manual_template_without_songs_prints_nothing(manual_template):
    """A template nobody picked songs for has nothing to print."""
    assert manual_template.get_songs() == []


def test_a_template_prints_one_untitled_section_by_default(category, song):
    """Templates without sections hand the renderer all their songs as a single section without a title."""
    assert category.get_sections() == [Section(None, [(1, song)])]


def test_the_default_section_is_in_song_number_order(manual_template, pdf_song, make_song):
    """The songs of a section are printed by number, whatever order the template returned them in."""
    PDFSong.objects.create(song=pdf_song, request=manual_template, song_number=2)
    first = make_song(name="First")
    PDFSong.objects.create(song=first, request=manual_template, song_number=1)

    assert manual_template.get_sections() == [Section(None, [(1, first), (2, pdf_song)])]


def test_manual_template_divides_its_songs_by_their_labels(manual_template, pdf_song, make_song, pdf_category):
    """A run of songs with one label is a section; songs without a label are untitled, and numbers order them."""
    songs = [make_song(pdf_category, name=name) for name in ("A", "B", "C", "D")]
    for number, song, section in [(4, songs[3], "Camp"), (1, pdf_song, ""), (3, songs[2], "Camp"), (2, songs[1], "")]:
        PDFSong.objects.create(song=song, request=manual_template, song_number=number, section=section)

    assert manual_template.get_sections() == [
        Section(None, [(1, pdf_song), (2, songs[1])]),
        Section("Camp", [(3, songs[2]), (4, songs[3])]),
    ]


def test_manual_template_titles_songs_without_a_section_after_a_titled_one(
    manual_template, pdf_song, pdf_category, make_song
):
    """Songs added to a template with sections come last without a label, and print as a section of their own."""
    added = make_song(pdf_category, name="Added")
    PDFSong.objects.create(song=pdf_song, request=manual_template, song_number=1, section="Camp")
    PDFSong.objects.create(song=added, request=manual_template, song_number=2)

    assert manual_template.get_sections() == [Section("Camp", [(1, pdf_song)]), Section("Ostatní", [(2, added)])]


def test_upload_path_is_namespaced_by_tenant(tenant, make_pdf_file):
    """Uploaded files are stored per tenant and day."""
    file = make_pdf_file()

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


def test_category_rows_number_the_wanted_songs_through_the_categories(sectioned, make_song):
    """Only the given songs are numbered, category by category, each under the first category it is in."""
    template, category, second, shared = sectioned
    only_second = make_song(second, name="Only second")
    make_song(category, name="Not wanted")

    assert category_rows(template.tenant, [only_second, shared]) == [
        (1, shared, category.name),
        (2, only_second, "Second"),
    ]


def test_category_rows_ask_the_database_once(sectioned, make_song, django_assert_num_queries):
    """However many categories and songs there are, the rows come from a single query."""
    template, category, second, shared = sectioned
    songs = [shared, make_song(second, name="Only second"), make_song(category, name="Only first")]

    with django_assert_num_queries(1):
        category_rows(template.tenant, songs)


def test_category_rows_keep_the_given_order_within_a_category(sectioned, make_song):
    """The songs of one category stay in the order they were given."""
    template, category, _second, shared = sectioned
    later = make_song(category, name="Later")

    assert [song for _number, song, _title in category_rows(template.tenant, [later, shared])] == [later, shared]


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
