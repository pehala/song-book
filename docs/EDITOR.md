# The song editor

`/add` and `/edit/<pk>` are Bootstrap pages (`backend/templates/backend/song_form.html`, chosen by `SongEditorMixin`),
not part of the reader. `SongForm.Media` loads `app/song.css`, `backend/editor.css`, `backend/editor.js` and
`backend/song_pdf_pages.js` (modules; the service worker does not precache them). The `text` widget
(`frontend/templates/markdownx/widget.html`) holds the lyrics textarea, the chord bar and the preview pane.

## Fields

The template places the name, the author and the capo itself; every other visible field of `SongForm` is listed after
them by `SongForm.detail_fields()` (categories first, through `field_order`), so a field added to `Song` shows up
without touching the template; the hidden fields are rendered next to the CSRF token. The PDF options (`pdf_columns`,
`pdf_keep_verses`) are among them.

The bar with the title and the buttons carries the indicator of whether the song fits a page of the PDF and its warnings
(`backend/pdf_pages.html`, driven by `song_pdf_pages.js`), so they are in view whichever section is open. Under the
fields the details panel shows the syntax help, a `<details>` that is open until closed. The Django admin has no such
bar, so its widget includes the indicator itself. `SongTextWidget` marks the widget as the editor page's
(`widget.editor`), which is also what gives the template its splitter and its tab panel attributes: the admin gets
neither.

## Preview

The preview is the server's: django-markdownx posts the text to `/markdownx/markdownify/`, which renders it with
`SONG_RENDERER`; nothing of the markup is rendered in JS. The line preview above the phone keyboard asks the same
endpoint.

## Layout

- There is one wide layout, from 1200px; anything narrower gets the tabs of a phone (Details, Lyrics, Preview). The
  details are never folded away: a tab below 1200px, a column beside the text boxes from there, which scrolls when it is
  longer than the screen and which an arrow on the panel itself folds into a rail (`sb-ed-folded`, kept as
  `sb-editor-details` in `localStorage`). The template marks the form with `data-show-details` when a song is being
  created or the form was refused (it has errors, whichever section they are in), and then the details are shown
  unfolded whatever was chosen.
- Layout is Bootstrap classes first; `editor.css` has only what Bootstrap lacks: the form sized to what the keyboard
  leaves through `--sb-vh`/`--sb-top`, the chord bar and 44 px rows. Below 1200px the sections are tabs that `editor.js`
  shows by toggling `d-none` on `[data-panel]` (their `d-xl-*` classes undo it above); without the script every
  section is shown. A `hidden` attribute does not beat `d-flex`, so put the flex on an inner element.
- The menus of the site header open over the sticky bar of the form (`#site-header` has a higher `z-index`).
- From 1200px a splitter between the lyrics and the preview, which `editor.js` drives with pointer events (it works by
  touch), sets the share of the width, kept in `localStorage` (`sb-editor-split`). The heights are not resizable: the
  text boxes fill the screen.

## Script

`editor.js` has no catalogue: every string it shows is rendered by the template, which `gettext` translates. It types
text (the fixed chord chips of `EDITOR_CHORDS`, `{}` completion, undo through `execCommand`), keeps the unsaved state, a
draft in `localStorage` under `sb-draft:<path>` and `Ctrl+S` = the "Save and continue" button, which posts `continue`
so `SongEditorMixin.get_success_url` returns to `/edit/<pk>` with `?next=` kept.

The draft survives a submit: it is marked as sent and stays until the server has saved the song, which
`SongEditorMixin.form_valid` tells through the `sb-saved` cookie (the quoted path of the page). The next load of that
page drops a sent draft whose save is confirmed and offers any other, so edits are not lost to a connection that failed.
Submitting clears the cookie first, and a page restored from the back-forward cache is not being submitted any more.
The line preview remembers the line it last asked the server for and does not ask again for the same one.

## Tests

`tests/e2e/editor/` and `tests/e2e/test_song_editor.py` drive all of it against the real Bootstrap from the CDN:
e2e tests stub nothing.
