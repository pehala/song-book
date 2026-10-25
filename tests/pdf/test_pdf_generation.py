"""Tests for the document handed to WeasyPrint, which is mocked throughout this module."""

from contextlib import nullcontext
from unittest.mock import patch

import pytest

from pdf.generate import CONTENTS_COLUMNS, generate_pdf
from pdf.models import Section

pytestmark = pytest.mark.django_db


def test_chords_are_raised_whatever_the_song_renderer(settings, mock_weasyprint, category, make_song, pdf_file):
    """WeasyPrint cannot lay out ruby text, so the document raises the chords with plain inline boxes."""
    settings.SONG_RENDERER = "chords.markdown.RUBY_RENDERER"
    make_song(category, text="{Ami}Hello {C}World")

    generate_pdf(pdf_file, category)

    html = mock_weasyprint.call_args.kwargs["string"]
    assert '<span class="chord" style="margin-right: -' in html
    assert ">Ami</span>Hello" in html
    assert ">C</span>World" in html
    assert "<ruby>" not in html


def test_link_is_a_clickable_anchor_with_a_scheme(mock_weasyprint, category, make_song, pdf_file):
    """The link of the template is printed and points to its URL, with https:// when none was typed."""
    make_song(category, text="Hello")
    category.link = "jerry.crazycactus.eu"

    generate_pdf(pdf_file, category)

    html = mock_weasyprint.call_args.kwargs["string"]
    assert '<a class="link" href="https://jerry.crazycactus.eu">https://jerry.crazycactus.eu</a>' in html


def test_contents_entries_do_not_set_the_footer_name(mock_weasyprint, category, make_song, pdf_file):
    """Only the contents heading and the song headings set the running name.

    A contents page that continues on the next one therefore keeps the heading in its footer.
    """
    make_song(category, text="Hello")

    generate_pdf(pdf_file, category)

    html = mock_weasyprint.call_args.kwargs["string"]
    contents = html.split('<ul class="contents-list">')[1].split("</ul>")[0]
    assert 'class="name"' not in contents


def test_contents_entry_links_only_the_title(mock_weasyprint, category, make_song, pdf_file):
    """The link wraps the plain title; the number and the page come from the entry's own pseudo-elements."""
    song = make_song(category, name="Hlupák Váhá", text="Hello")

    generate_pdf(pdf_file, category)

    html = mock_weasyprint.call_args.kwargs["string"]
    assert (
        f'<li data-number="1" data-target="#{song.id}-title"><a href="#{song.id}-title">Hlupák Váhá</a></li>'
    ) in html


def test_contents_have_a_header_over_every_column_in_the_language_of_the_template(
    mock_weasyprint, category, make_song, pdf_file
):
    """The header names the columns of each of the contents columns.

    It is in the page once and once more as the running element that repeats it on the later contents pages.
    """
    category.locale = "cs"
    make_song(category, text="Hello")

    with patch("pdf.generate.changed_locale", nullcontext):
        generate_pdf(pdf_file, category)

    html = mock_weasyprint.call_args.kwargs["string"]
    assert html.count('class="contents-head"') == 2
    assert html.count('class="running-head"') == 1
    for label in ("head-number", "head-title", "head-page"):
        assert html.count(f'class="{label}"') == 2 * CONTENTS_COLUMNS
    assert html.count(">Číslo</span>") == 2 * CONTENTS_COLUMNS
    assert html.count(">Název</span>") == 2 * CONTENTS_COLUMNS
    assert html.count(">Strana</span>") == 2 * CONTENTS_COLUMNS


def test_no_anchor_without_a_link(mock_weasyprint, category, make_song, pdf_file):
    """A template without a link prints no anchor."""
    make_song(category, text="Hello")
    category.link = ""

    generate_pdf(pdf_file, category)

    assert 'class="link"' not in mock_weasyprint.call_args.kwargs["string"]


@pytest.fixture
def two_sections(monkeypatch, category, make_song):
    """The category prints two songs in a section called Hymns and one in Camp."""
    songs = [make_song(category, name=name, text="Hello") for name in ("Zebra", "Mule", "Apple")]
    monkeypatch.setattr(
        type(category),
        "get_sections",
        lambda self: [Section("Hymns", [(1, songs[0]), (2, songs[1])]), Section("Camp", [(3, songs[2])])],
    )
    return songs


def test_a_titled_section_starts_with_a_label_on_the_page_of_its_first_song(
    mock_weasyprint, category, pdf_file, two_sections
):
    """The label sits in the article of the first song, which therefore starts the section's page.

    The later songs of the section get none.
    """
    zebra, mule, apple = two_sections

    generate_pdf(pdf_file, category)

    html = mock_weasyprint.call_args.kwargs["string"]
    assert 'section-start">\n              <h1 class="section-title" id="section-1">Hymns</h1>' in html
    assert '<h1 class="section-title" id="section-2">Camp</h1>' in html
    assert html.count('class="section-title"') == 2
    positions = [html.index(marker) for marker in ('id="section-1"', f'id="{zebra.id}-title"', f'id="{mule.id}-title"')]
    assert positions == sorted(positions)
    assert html.index(f'id="{mule.id}-title"') < html.index('id="section-2"') < html.index(f'id="{apple.id}-title"')


def test_contents_head_each_section_with_a_link_to_its_label(mock_weasyprint, category, pdf_file, two_sections):
    """The contents have a heading per titled section that links to the label, and sort the songs inside sections."""
    generate_pdf(pdf_file, category)

    html = mock_weasyprint.call_args.kwargs["string"]
    contents = html.split('<ul class="contents-list">')[1].split("</ul>")[0]
    assert contents.count('class="contents-section"') == 2
    heading = '<li class="contents-section" data-target="#section-1"><a href="#section-1">Hymns</a></li>'
    assert heading in contents
    order = [contents.index(text) for text in ("Hymns", "Mule", "Zebra", "Camp", "Apple")]
    assert order == sorted(order)


def test_untitled_sections_print_no_labels(mock_weasyprint, category, make_song, pdf_file):
    """A template without sections renders no section label and no section heading in the contents."""
    make_song(category, text="Hello")

    generate_pdf(pdf_file, category)

    html = mock_weasyprint.call_args.kwargs["string"]
    assert "section-title" not in html
    assert "contents-section" not in html
