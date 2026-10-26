"""Browser tests of the song editor."""

from playwright.sync_api import expect

# Short lines with chords: too tall for the two columns of a page, but not for three
NARROW_TEXT = "\n".join(f"{{C}}Line {number}" for number in range(75))


def test_the_editor_tells_whether_the_song_fits_on_a_page_of_the_pdf(page, library, staff_user, sign_in, song):
    """The indicator follows the lyrics and the columns as they change: a check mark while the song fits."""
    sign_in(staff_user)
    page.goto(f"/edit/{song.pk}")
    indicator = page.locator("[data-pdf-pages]")

    expect(indicator).to_contain_text("✓")
    expect(indicator).to_contain_text("Fits on one page of the PDF")

    page.locator("#id_text").fill(NARROW_TEXT)
    expect(indicator).to_contain_text("⚠")
    expect(indicator).to_contain_text("Might not fit on one page of the PDF")

    page.locator("#id_pdf_columns").select_option("3")
    expect(indicator).to_contain_text("✓")


def test_the_editor_of_a_new_song_shows_nothing_until_there_is_text(page, library, staff_user, sign_in):
    """There is nothing to lay out in an empty song."""
    sign_in(staff_user)
    page.goto("/add")
    indicator = page.locator("[data-pdf-pages]")

    expect(indicator).to_be_hidden()

    page.locator("#id_text").fill("{C}Hello")
    expect(indicator).to_contain_text("✓")


def test_the_editor_warns_that_a_song_with_long_lines_is_cramped_in_three_columns(
    page, library, staff_user, sign_in, song
):
    """Lines of chords that wrap in the narrow columns make the song look cramped, which only three columns do."""
    sign_in(staff_user)
    page.goto(f"/edit/{song.pk}")
    cramped = page.locator(".pdf-pages-cramped")
    page.locator("#id_text").fill(
        "\n".join("{C}A line of words that is far {G}too long for a column" for _ in range(20))
    )

    expect(cramped).to_be_hidden()

    page.locator("#id_pdf_columns").select_option("3")
    expect(cramped).to_be_visible()
    expect(cramped).to_contain_text("Might look cramped in three columns, many lines wrap there")

    page.locator("#id_text").fill(NARROW_TEXT)
    expect(cramped).to_be_hidden()
