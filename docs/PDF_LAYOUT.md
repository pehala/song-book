# PDF layout

How the songbook PDF is laid out by `pdf/templates/pdf/index.html` and `pdf/static/pdf.css`, which WeasyPrint
renders (`docs/FILES.md` describes the template/file workflow).

## Page

* The margins are 2 cm at the top and bottom and 1.5 cm at the sides, the least a printer reliably reaches. The
  header and footer margin boxes sit in the top and bottom margins, so those stay at 2 cm.
* Each song starts on a page of its own and fills two columns of `.text`. The song heading is 20 pt and the author
  line 12 pt, and `.text` has a line height of 1.25, so most songs fit on one page.

## Chords

PDFs always use `PDF_RENDERER` (`Song.pdf_markdown`), whatever `SONG_RENDERER` says and never from the
`prerendered` column. Its `raised` plugin (`chords/plugins/raised.py`) prints each chord above the word it belongs
to.

### Markup and CSS

* `{Ami}word` becomes `<span class="chord" style="margin-right: -1.977em">Ami</span>word`.
* `.chord` in `pdf.css` raises the span with `vertical-align`, so only lines that carry chords grow, and keeps it on
  one line (`white-space: nowrap`).
* The negative margin cancels the width of the chord, so the word starts under its left edge. The width is the
  advance of the chord in Open Sans Bold, read from the font files with fontTools; kerning is ignored.
* A chord wider than its word is followed by the missing room (`padding-right` on a span around the word, plus
  `CHORD_GAP`), so the pair is as wide as the wider of the two. Chords never overlap, lines wrap as plain text and
  justified paragraphs stay justified.
* `CHORD_SCALE` in the plugin must match the font size of `.chord` in `pdf.css`.

### Which word a chord stands over

* The plain word that touches the chord: `{C}stojí`, or `ráda` in `kama{C}ráda`.
* Otherwise the next plain word after spaces, as in `{C} stojí`; the spaces are dropped.
* Otherwise none, when another chord, markup or `/n/` spaces follow: the chord keeps its own width plus `CHORD_GAP`
  and the spaces stay.
* None at the end of a line (`často sleví, {F#7}`): the chord takes no room and hangs over the end of the line. A
  full line would otherwise wrap the chord onto a row of its own.

### Known limits

* A short word under a long chord leaves a gap after it.
* Copying text out of the PDF gives `AmiMám`, with no space between chord and word.
* Rows with chords are taller, so a song with many chords may need an extra page.

## Table of contents

`#contents` holds the title, the date, the header link, the contents heading, the header of the columns and the list.
The entries are sorted by title in the collation of the template's language and carry the number of the song.

* The list has `CONTENTS_COLUMNS` columns (`pdf/generate.py`); the `columns` of `.contents-list` in `pdf.css` must
  match.
* An entry is `<span class="number">`, the title and `<span class="last-word" href="…">`. The number is positioned
  absolutely in a 26 pt gutter and the link has `padding-left` of the same width, so a title that wraps hangs under its
  first line. `without_last_word` and `last_word` (`pdf/templatetags/contents.py`) split the title.
* `.last-word::after` is a no-break space, `leader('.')`, a no-break space and `target-counter(attr(href), page)`, the
  page of the song heading. `white-space: nowrap` on the span keeps the last word, the dots and the page number on one
  line, so a wrapped title has them on its last line only and never a line made of dots. `attr(href)` is read from the
  span, which is why it carries the `href`.
* The number is not a negative `text-indent` because WeasyPrint then sizes the leader of the first line without
  that indent and the dots stop short of the right edge.
* `contents_head.html` is the header (number, song title, page) of every column. It is included twice: in the flow
  above the list, and inside `.running-head`, which `position: running(contents-head)` takes out of the flow.
  `#contents` has `page: contents`, so `@page contents` prints the running header in the `@top-center` margin box of every
  contents page, and `@page contents:first` keeps the `title` string there on the first page, which has the header
  in the flow. `.running-head` has the 8 px side padding of the body so its columns line up with the list.
* A named page forces a page break between it and the content before it, so the header link lives inside `#contents`
  and not before it.
* Pages with the running header put the header link at the top of its margin box (`@page contents:nth(n+2)`), because
  the header link and the running header otherwise share the same strip.
* With a cover image the contents start on page 2 (`.date` breaks before it), so `contents:first` has no
  `@top-center` and page 2, which has the header in the flow, shows the `title` string; the running header starts on
  page 3.

## Header link

* `PDFTemplate.link` is free text. `PDFTemplate.link_url` returns it with `https://` in front unless it names a
  scheme (`scheme://` or `mailto:`), and the template only uses `link_url`.
* The template writes `<a class="link" href="{{ link_url }}">` first in `#contents`. `position: running(link)` takes it
  out of the flow and `content: element(link)` puts it in the `@top-right` margin box of every page. A string in
  `content` would only be text, while an element keeps its hyperlink.
* `.link` sets the 9 pt size of the margin box and no underline, because a running element keeps the font size of the
  body.

## Running strings

`string-set` copies text into the margin boxes: `title` (top centre), `date` (bottom centre) and `name` (bottom
right). `string(name)` is the first value set on the page, and a page that sets none keeps the last one of the pages
before it.

* The contents heading and the song headings carry `.name`. The entries of the table of contents do not, so every page
  of a contents that spans several pages shows "Table of Contents" in its footer. Give an element `.name` only when it
  should replace the footer text.
