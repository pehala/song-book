"""Browser tests of the page that orders the songs of a file template into sections."""

import pytest
from django.urls import reverse
from playwright.sync_api import expect

from backend.models import Song
from pdf.models import Section
from pdf.models.request import ManualPDFTemplate, PDFSong


@pytest.fixture(autouse=True)
def offline_cdn(page):
    """Bootstrap comes from a CDN; the page works without it, so tests do not wait for it."""
    page.route("https://cdn.jsdelivr.net/**", lambda route: route.fulfill(body="", content_type="text/plain"))


@pytest.fixture
def template(library):
    """A file template with the three songs of the first category, in a section of their own except the first."""
    template = ManualPDFTemplate.objects.create(tenant=library, name="Campfire", filename="campfire", locale="en")
    for number, (name, section) in enumerate([("Hrad", ""), ("Jožin z bažin", "Camp"), ("Both Songs", "Camp")], 1):
        PDFSong.objects.create(song=Song.objects.get(name=name), request=template, song_number=number, section=section)
    return template


@pytest.fixture
def order_page(page, template, staff_user, sign_in):
    """The page that orders the songs of the template, reached through the song selection like a user would."""
    sign_in(staff_user)
    page.goto(reverse("pdf:templates:edit", kwargs={"pk": template.pk}))
    page.get_by_role("button", name="Finish selecting").click()
    expect(page.locator("#sortable")).to_be_visible()
    # The script of the page is a module, which runs after the page is shown; it makes the list sortable last
    page.wait_for_function("() => window.jQuery && jQuery('#sortable').data('ui-sortable')")
    return page


def rows(page):
    """The order list as text: the title of a section heading, or the name of a song with its number."""
    return page.evaluate(
        """() => [...document.querySelectorAll('#sortable > div')].map(row => row.classList.contains('section-row')
            ? '# ' + row.querySelector('input').value
            : row.querySelector('input[type=number]').value + ' ' + row.querySelector('input[type=text]').value)"""
    )


def finish(page):
    """Submits the page that orders the songs and waits for the list of templates."""
    page.get_by_role("button", name="Finish").click()
    page.wait_for_url("**/pdf/templates/")


def test_the_page_shows_the_sections_of_the_template(order_page):
    """A heading stands before the first song of each section, none before songs without one."""
    assert rows(order_page) == ["1 Hrad", "# Camp", "2 Jožin z bažin", "3 Both Songs"]


def test_finishing_keeps_the_sections(order_page, template):
    """Submitting the page unchanged stores what it showed."""
    finish(order_page)

    assert template.get_sections() == [
        Section(None, [(1, Song.objects.get(name="Hrad"))]),
        Section("Camp", [(2, Song.objects.get(name="Jožin z bažin")), (3, Song.objects.get(name="Both Songs"))]),
    ]


def test_finishing_keeps_the_numbers_typed_in(order_page, template):
    """Submitting does not renumber the songs, only dragging does."""
    numbers = order_page.locator(".song-row input[type=number]")
    for index, number in enumerate(["10", "20", "30"]):
        numbers.nth(index).fill(number)
    finish(order_page)

    assert sorted(number for number, _song in template.get_songs()) == [10, 20, 30]


def test_a_section_added_at_the_top_takes_the_songs_below(order_page, template):
    """The new heading is first in the list, so every song belongs to it until another heading."""
    order_page.get_by_role("button", name="Add section").click()
    order_page.get_by_placeholder("Section title").first.fill("Evening")

    assert rows(order_page) == ["# Evening", "1 Hrad", "# Camp", "2 Jožin z bažin", "3 Both Songs"]
    finish(order_page)

    assert [section.title for section in template.get_sections()] == ["Evening", "Camp"]


def test_removing_a_heading_merges_its_songs_into_the_section_above(order_page, template):
    """The songs of a removed heading continue the section before it, which here is none."""
    order_page.get_by_role("button", name="Remove section").first.click()
    finish(order_page)

    assert [section.title for section in template.get_sections()] == [None]


def test_dragging_a_heading_moves_where_the_section_starts(order_page, template):
    """The songs the heading passes change section, and the numbers follow the order."""
    heading = order_page.locator(".section-row").first
    heading.locator("span").drag_to(order_page.locator(".song-row").first)

    assert rows(order_page) == ["# Camp", "1 Hrad", "2 Jožin z bažin", "3 Both Songs"]
    finish(order_page)

    assert [(section.title, [number for number, _song in section.songs]) for section in template.get_sections()] == [
        ("Camp", [1, 2, 3])
    ]


def test_sorting_by_name_keeps_the_songs_in_their_sections(order_page, template):
    """Songs are sorted inside a section and never move across a heading."""
    order_page.get_by_role("button", name="Sort by name").click()

    assert rows(order_page) == ["1 Hrad", "# Camp", "2 Both Songs", "3 Jožin z bažin"]
