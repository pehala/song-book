# PDF layout

How the songbook PDF is laid out by `pdf/templates/pdf/index.html` and `pdf/static/pdf.css`, which WeasyPrint
renders (`docs/FILES.md` describes the template/file workflow).

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

## Header link

* `PDFTemplate.link` is free text. `PDFTemplate.link_url` returns it with `https://` in front unless it names a
  scheme (`scheme://` or `mailto:`), and the template only uses `link_url`.
* The template writes `<a class="link" href="{{ link_url }}">` first in the body. `position: running(link)` takes it
  out of the flow and `content: element(link)` puts it in the `@top-right` margin box of every page. A string in
  `content` would only be text, while an element keeps its hyperlink.
* `.link` sets the 9 pt size of the margin box and no underline, because a running element keeps the font size of the
  body.
