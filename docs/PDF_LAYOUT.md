# PDF layout

How the songbook PDF is laid out by `pdf/templates/pdf/index.html` and `pdf/static/pdf.css`, which WeasyPrint
renders (`docs/FILES.md` describes the template/file workflow).

## Page

* The margins are 2 cm at the top and bottom and 1.5 cm at the sides, the least a printer reliably reaches. The
  header and footer margin boxes sit in the top and bottom margins, so those stay at 2 cm.
* Each song starts on a page of its own and fills two columns of `.text`. The song heading is 20 pt and the author
  line 12 pt, and `.text` has a line height of 1.25, so most songs fit on one page.
* `Song.pdf_columns` (2 by default, or 3) sets the number of columns of one song, as the class `columns-<n>` of
  `.text`. A narrow song whose lines stay short enough not to wrap in a column of about 5.3 cm fits on one page in three
  columns where two would need a second page; a song with long lines wraps in them, so it keeps two.
* `Song.pdf_keep_verses` (off by default) adds the class `keep-verses` to `.text`, whose `p` elements, the verses, then
  never split between two columns (`break-inside: avoid-column`). Without it the columns are balanced by height and cut
  a verse where they meet, which happens in about half of a songbook. A song with a verse too long to share a column
  with the others then needs a second page, and WeasyPrint lays such a song out several times slower, so the option is
  set per song for the songs that benefit. The overflow estimate below does not know about it.

### Overflow estimate

The song editor tells whether the song fits on one page without rendering it: `backend/static/backend/song_pdf_estimate.js`
adds up the height of the lines. A source line takes `ceil(visible characters / W)` lines of 16.67 px, where the visible
characters leave out `{chords}` and count `/n/` as n spaces and `W` is 52 in two columns and 31 in three; a line with
chords adds 11.85 px, each gap between stanzas 13.3 px and the heading 27 px. The song fits when the sum is at most
872 px (the room of a column) times the number of columns; within 2 % of that the editor only says the song is close.
The constants were fitted to the page counts of a whole songbook, so they change with `.text`, the page margins or the
heading in `pdf.css`. The heading is a single line in the estimate, so a title long enough to wrap is not counted.

In three columns the editor also warns when more than 7 % of the lines carry chords and are longer than `W`. Such a line
wraps in the narrow column, is taller, can leave its last chord alone on a row above the orphaned word and stretches
the justified text; a plain line that wraps reads as prose and is not counted. In the songbook that rule separates the
songs that look cramped (a refrain of wrapping chord lines, 9 % and more) from those that do not (4.6 % and less).

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
* An entry is an `li` with `data-number` (the number of the song) and `data-target` (the `#id` of the song heading)
  around an `<a>` holding the plain title. WeasyPrint makes a link of every box inside an `<a>`, so the link has no
  boxes in it and is one link (one per line of a title that wraps); the number and the page are not part of it.
  `li::before` draws the number absolutely in a 26 pt gutter and the `li` has `padding-left` of the same width, so a
  title that wraps hangs under its first line.
* `li::after` is a no-break space, `leader('.')`, a no-break space and `target-counter(attr(data-target), page)`, the
  page of the song heading. The no-break space keeps the dots with the last word of the title, so a wrapped title has
  them on its last line only and never a line made of dots.
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

## Sections

`PDFTemplate.get_sections()` returns the songs as `Section`s, a title and the numbered songs of one run; the numbers
are those of the whole PDF. A section without a title (the default) adds nothing to the layout, so only the first
section of a PDF may be untitled: `group_sections` titles a later one "Other", or its songs would be printed under the
heading and the running name of the section before it.

* The first song of a titled section starts with `<h1 class="section-title">`: a small uppercase label over a rule,
  on the page of the song and not on a page of its own. `.section-start` breaks before the article, so the song
  heading, which breaks before every `h2`, does not leave the label alone on a page. `h1` and `h2` nest the PDF
  bookmarks by section.
* The label sets the `title` string, which the `@top-center` box of the song pages prints as
  `string(title, first-except)`: the section name on the pages after the label and nothing on the page that
  carries it. Pages before any section (the cover and contents have their own boxes) keep the title of the
  document.
* The contents list one `li.contents-section` per titled section before its songs, in the style of an entry: the
  title, dots and the page of the label, linked to `#section-<n>`. The songs of a section are sorted by title
  among themselves, so the numbers of a section need not ascend.

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
