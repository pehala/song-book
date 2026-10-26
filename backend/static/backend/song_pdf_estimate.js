// Estimates the height of a song in a PDF from its lines, so the editor can tell whether it fits on one page.
// The constants follow pdf.css (`.text` in two or three columns, 10 pt text, line height 1.25, 20 pt heading) and were
// fitted to the page counts of a whole songbook rendered by WeasyPrint; change them together with the layout.

// Height of the heading and the author line, in CSS px
const HEADING = 27;
// Height of a line of text, of the extra a line with chords takes for the raised chords, and of the gap between stanzas
const LINE = 16.67;
const CHORD_LINE = 11.85;
const GAP = 13.3;
// Characters that fit on a line of a column, by the number of columns of the song, and the height of a column of a page
const LINE_CHARS = { 2: 52, 3: 31 };
const COLUMN_HEIGHT = 872;

const CHORD = /\{(?!\s)[^}]+?\}/;
const CHORD_G = new RegExp(CHORD, "g");
const SPACES = /\/(\d+)\//g;

// Returns the number of characters of a source line on the page, which leave out the chords and count the spaces.
function visibleLength(line) {
  return line.replaceAll(CHORD_G, "").replace(SPACES, (_, count) => " ".repeat(count)).length;
}

// Returns the estimated height of the lines of the song, set in the given number of columns, added up in CSS px.
export function songHeight(text, columns) {
  const lineChars = LINE_CHARS[columns];
  let height = HEADING;
  let gap = false;
  let started = false;
  for (const line of text.split("\n")) {
    if (!line.trim()) {
      gap = started;
      continue;
    }
    if (gap) {
      height += GAP;
    }
    gap = false;
    started = true;
    height += LINE * Math.ceil(visibleLength(line) / lineChars);
    if (CHORD.test(line)) {
      height += CHORD_LINE;
    }
  }
  return height;
}

// Returns the estimated height of the song relative to the room the columns of a page have, 1 being a full page.
export function pageFill(text, columns) {
  return songHeight(text, columns) / (columns * COLUMN_HEIGHT);
}

// Returns the share of the lines of the song that carry chords and wrap in the given number of columns. A wrapped line of
// chords is taller, can leave a chord alone above the last word and stretches the justified text, unlike a wrapped line
// of plain text, which reads as prose.
export function wrappedChordShare(text, columns) {
  const lines = text.split("\n").filter((line) => line.trim());
  const wrapped = lines.filter((line) => CHORD.test(line) && visibleLength(line) > LINE_CHARS[columns]);
  return lines.length ? wrapped.length / lines.length : 0;
}
