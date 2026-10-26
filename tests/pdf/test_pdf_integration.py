"""Integration test for the full WeasyPrint PDF rendering path.

This test calls generate_pdf() with NO mocking of WeasyPrint itself.
It exercises the complete pipeline: Django template rendering → WeasyPrint
HTML parsing → PDF byte stream → FileField save.

The test is intentionally slow (real PDF rendering) and is isolated in its
own module so it can be skipped in fast-feedback CI runs with:

    pytest -m "not slow"

Requires that static files (pdf.css, OpenSans fonts) are present on disk,
which they are as part of the source tree (pdf/static/).
"""

import pytest
from django_weasyprint.utils import DjangoURLFetcher
from weasyprint import HTML

from backend.models import Song
from pdf.generate import generate_pdf, get_base_url
from pdf.models import Status

pytestmark = [pytest.mark.django_db, pytest.mark.slow]


def test_full_pdf_generation_produces_valid_pdf_bytes(pdf_category, pdf_song, make_pdf_file):
    """End-to-end: generate_pdf() produces a real PDF file starting with %PDF.

    No WeasyPrint mocking. Verifies:
    - status transitions to DONE
    - a file is written to the filesystem
    - the file starts with the standard PDF header b"%PDF"
    - the output is non-trivial (> 1 kB)
    """
    pdf_file = make_pdf_file(pdf_category)

    success, _ = generate_pdf(pdf_file, pdf_category)

    pdf_file.refresh_from_db()

    assert success is True, "generate_pdf() returned False; check logs for errors"
    assert pdf_file.status == Status.DONE
    assert pdf_file.file, "PDFFile.file should be set after successful generation"
    assert pdf_file.file.name.endswith(".pdf")

    # Read the first bytes from the generated file to verify it is a real PDF
    with pdf_file.file.open("rb") as fh:
        header = fh.read(4)
    assert header == b"%PDF", f"File does not start with PDF header; got {header!r}"

    # Sanity-check that the output is non-trivially sized
    assert pdf_file.file.size > 1024, f"Generated PDF is suspiciously small: {pdf_file.file.size} bytes"

    # Clean up the generated file so it does not accumulate between test runs
    pdf_file.file.delete(save=False)


def test_contents_of_a_long_songbook_fit_on_the_first_page(mock_weasyprint, pdf_category, make_pdf_file, make_song):
    """120 songs are listed on the page of the title, so the first song starts on the second page."""
    songs = [make_song(pdf_category, name=f"Song {number}", text="Hello") for number in range(120)]
    generate_pdf(make_pdf_file(pdf_category), pdf_category)

    document = HTML(
        string=mock_weasyprint.call_args.kwargs["string"], url_fetcher=DjangoURLFetcher(), base_url=get_base_url()
    ).render()

    first_song_page = next(index for index, page in enumerate(document.pages) if f"{songs[0].id}-title" in page.anchors)
    assert first_song_page == 1


def test_contents_entry_is_a_single_link(mock_weasyprint, pdf_category, make_pdf_file, make_song):
    """A short entry of the table of contents is one link, not one for the number, the words and the dots."""
    songs = [make_song(pdf_category, name=f"Song number {number}", text="Hello") for number in range(3)]
    generate_pdf(make_pdf_file(pdf_category), pdf_category)

    document = HTML(
        string=mock_weasyprint.call_args.kwargs["string"], url_fetcher=DjangoURLFetcher(), base_url=get_base_url()
    ).render()

    targets = [target for link_type, target, *_ in document.pages[0].links if link_type == "internal"]
    assert sorted(targets) == sorted(f"{song.id}-title" for song in songs)


@pytest.fixture
def render_song_pages(mock_weasyprint, pdf_category, make_pdf_file):
    """Returns a function that renders a PDF of one narrow song and returns the pages from the song on.

    The generation only captures the HTML, which is then laid out by WeasyPrint here, so the pages are real.
    """

    def render(text=None, **song_fields):
        stanza = "\n".join(f"{{C}}Short line {{G}}{line}" for line in range(4))
        song = Song.objects.create(name="Narrow Song", text=text or "\n\n".join([stanza] * 16), **song_fields)
        song.categories.add(pdf_category)
        generate_pdf(make_pdf_file(pdf_category), pdf_category)

        document = HTML(
            string=mock_weasyprint.call_args.kwargs["string"], url_fetcher=DjangoURLFetcher(), base_url=get_base_url()
        ).render()

        first_song_page = next(index for index, page in enumerate(document.pages) if f"{song.id}-title" in page.anchors)
        return document.pages[first_song_page:]

    return render


def test_a_narrow_song_overflows_in_two_columns(render_song_pages):
    """The song of the next test needs more than one page in the default two columns."""
    assert len(render_song_pages()) == 2


def test_a_song_of_three_columns_fits_on_one_page(render_song_pages):
    """A song with `pdf_columns` of 3 is set in three columns, which fit it on the page it overflows in two."""
    assert len(render_song_pages(pdf_columns=Song.PDFColumns.THREE)) == 1


def count_verse_fragments(pages):
    """Returns the number of block boxes the `p` elements of the pages are laid out in, and the number of elements."""
    boxes = []

    def walk(box):
        if box.element_tag == "p" and type(box).__name__ == "BlockBox":
            boxes.append(box.element)
        for child in getattr(box, "children", ()):
            walk(child)

    for page in pages:
        walk(page._page_box)
    return len(boxes), len(set(map(id, boxes)))


@pytest.fixture
def three_verses():
    """Returns the text of three verses of 20 lines, which balanced over two columns cut the second one."""
    verse = "\n".join(f"Line {line} of the verse" for line in range(20))
    return "\n\n".join([verse] * 3)


def test_a_verse_splits_between_two_columns(render_song_pages, three_verses):
    """The columns are balanced by height, so the second of three verses starts in one and ends in the other."""
    fragments, verses = count_verse_fragments(render_song_pages(three_verses))
    assert fragments == verses + 1


def test_a_song_keeping_its_verses_together_does_not_split_them(render_song_pages, three_verses):
    """A song with `pdf_keep_verses` lays each verse out in one column, on the page the song fits."""
    pages = render_song_pages(three_verses, pdf_keep_verses=True)
    fragments, verses = count_verse_fragments(pages)
    assert len(pages) == 1
    assert fragments == verses
