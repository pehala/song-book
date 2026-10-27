# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**chords** — a multi-tenant Django songbook (`https://github.com/pehala/song-book`). Songs are
written in Markdown with a custom chord syntax, served **once** as JSON to the browser, and
filtered/searched entirely client-side so the site stays usable on a bad connection (camps,
wilderness). It also generates printable PDF songbooks asynchronously.

Stack: Python 3.14, Django 6, `uv`. Production runs PostgreSQL plus Redis (both the cache and
the Huey queue) under gunicorn behind nginx, which serves fingerprinted static files
pre-compressed with brotli (`brotli_static`) and long-lived cache headers; dev and tests use
SQLite and an in-memory cache.

## Commands

Everything runs through `uv`. **Never invoke bare `python`/`pytest`.**

```bash
uv sync --group dev                 # install deps (dev group)
make dev                            # dev server on SQLite (chords.settings.development): no make init, no Redis; PORT, DB_FILE
make init                           # cp production.py.tpl -> production.py, then migrate
make run                            # dev server (SETTINGS=chords.settings.production, needs Redis)
make worker                         # Huey worker for PDF generation
make test                           # uv run --group dev pytest tests/
make coverage                       # the same, with a branch coverage report
make e2e                            # Playwright tests of the reader (needs `uv run playwright install --with-deps chromium`)
make commit-acceptance              # what CI gates on: ruff --fix + ruff format + check-fuzzy + check-messages
make deploy                         # migrate + prerender + compilemessages + collectstatic
make help                           # all targets
```

Testing server: `make dev` (SQLite, no Redis, no `make init`) serves on `PORT` (default in the Makefile) using
`db.sqlite3` of the working tree, or the file named by `DB_FILE`. In a git worktree there is no `db.sqlite3` yet (it is
git-ignored), so copy the main checkout's first with `cp ../db.sqlite3 db.sqlite3`: a copy, not a symlink, because
`make dev` runs `migrate` and the worktree's migrations must not touch the main checkout's data.

Single test / subset:

```bash
uv run --group dev pytest tests/backend/test_etag.py::test_response_has_etag -v
uv run --group dev pytest tests/ -k cache
uv run --group dev pytest tests/ -m "not slow and not e2e"    # skip the real WeasyPrint renders
```

Management commands: `uv run python manage.py <cmd>` — notably `prerender`,
`clear_prerender`, `import -c <category_id> <file.json>`, `generate_pdf`, `run_huey`.

## Settings

`chords/settings/base.py` holds the shared defaults, custom settings and cache-key names; `development.py` (`make dev`),
`production.py`, `container.py` and `test.py` override it and say how in their docstrings. `production.py` is **not
committed**: `make init` generates it from `production.py.tpl`.

`manage.py` and the Makefile default to `chords.settings.production`, so **a fresh clone cannot run anything until
`make init` has created that file**, except `make dev`, which passes `--settings` itself. pytest is pinned to
`chords.settings.test` in `pyproject.toml`.

Base settings use `chords.storage.ManifestStorage`, a `ManifestStaticFilesStorage` that also rewrites
`import … from "./x.js"` inside hashed modules; tests must not use it (hence the override) because no manifest is
collected. Hashed URLs are only emitted with `DEBUG = False`. `SECURE_CSP` (Django 6 CSP middleware) is enforced:
adding a CDN script or inline style means editing that policy.

## Multi-tenancy

One deployment serves several songbooks, told apart by `Host` header.

- `tenants/middleware.py` resolves `Tenant` by `hostname` and sets `request.tenant` plus
  `request.user.is_localadmin` on **every** request. Unknown host → 404, except under `DEBUG`
  where it falls back to `Tenant.objects.first()`.
- `tenants/migrations/0001_initial.py` creates a default tenant with
  `hostname=settings.TENANT_HOSTNAME` (`"localhost"`). Tests must `get_or_create` it, not
  `create` it, and the test `Client` needs `HTTP_HOST="localhost"` for the middleware to resolve.
- `Song` has **no** FK to `Tenant`. The path is always `song → categories → tenant`, which is why
  tenant-scoped song querysets filter on `categories__tenant` and `.distinct()`.
- Every cache key is namespaced: `tenant_cache_key(tenant, key)` → `f"{tenant.id}-{key}"`
  (`tenants/utils.py`).

## Apps

`backend` (`Song`, the songs payload, `/api/me`, generic CRUD base views, auth helpers, management commands), `category`,
`pdf`, `tenants`, `analytics` and `frontend` (no models: the reader and the Bootstrap base templates of the admin
pages). Worth knowing before editing:

- `Category` is a **subclass of `pdf.PDFTemplate`**.
- **CRUD views** inherit `UniversalCreateView`/`UniversalUpdateView`/`UniversalDeleteView` from
  `backend/generic.py` (success messages, `?next=` redirect, `base/verbs/*.html` templates).
  Access control is `LocalAdminRequired` / `SuperAdminRequired` from `backend/mixins.py`, backed
  by `backend/auth.py`.
- **Navigation** is drawn client-side by the shared header from the tenant's bootstrap (`tenants/bootstrap.py`),
  whose categories, PDFs and links come from the cached menus in `tenants/menus.py`.
- **URLs**: `backend.urls` is mounted at `^` (so `/`, `/all`, `/api/songs`, `/api/me`, `/add`,
  `/edit/<pk>`), `frontend.urls` serves `/service_worker.js` and `/manifest.webmanifest`, categories live at
  `/categories/<slug>`, plus `/pdf/`, `/analytics/`, `/tenants/`,
  `/admin/`. `/`, `/all` and `/categories/<slug>` all route to `frontend.views.ShellView`.

## Song rendering pipeline

Markdown → HTML happens through the mistune instances of `chords/markdown.py`, each with three
local plugins in `chords/plugins/`: a chord plugin — `inline` (`{Ami}` → `<span class="chord">`), `ruby`
(`{Ami}word` → `<ruby>word<rt class="chord">`) or `raised` (PDF only) — `paragraph` and `spaces`.
`INLINE_RENDERER` uses the first, `RUBY_RENDERER` the second, and the `SONG_RENDERER` setting (a dotted path,
`RUBY_RENDERER` by default) picks the one used for songs and for django-markdownx's preview; a changed
renderer needs `manage.py prerender`.

PDFs use `PDF_RENDERER` (`Song.pdf_markdown`) instead, whatever `SONG_RENDERER` says; `docs/PDF_LAYOUT.md`
describes how their chords, header link and running footer are laid out.

`Song.rendered_markdown` chooses between rendering on the fly and the stored `prerendered`
column, controlled by two settings:

- `USE_PRERENDERED_MARKDOWN` — serve `Song.prerendered` instead of re-rendering.
- `USE_DYNAMIC_PRERENDER` — when a song has no prerendered HTML, render and save it on first
  request; with both the first off and the second off, a missing value raises.

`make deploy` runs `manage.py prerender` to fill the column for every song.

## The reader

The reader is a Preact + htm single page app with no build step; the rest (CRUD, PDF, analytics, login, `/admin/`)
keeps its Django templates and Bootstrap. `docs/READER.md` describes the modules, the shell, the header, the service
worker and the client state. Rules:

- Modules live in `frontend/static/app/` and are listed once in `frontend.views` (`MODULES`, `SITE_ENTRY`,
  `PAGE_ENTRIES`/`PAGE_MODULES`, `STYLESHEETS`); a new file must be added there. Keep modules free of import cycles and
  `import()` out of modules with nested template literals: `ManifestStorage` cannot see past them.
- `ShellView` serves one page for `/`, `/all` and `/categories/<slug>` and reads no user, session, message, CSRF or
  language, so it has no `Vary: Cookie`: the service worker serves one cached copy to every route and every user.
  `/api/me` is the only place that knows the user.
- A menu entry is added in `header.js` only; header markup and `header.css` use `sb-` prefixed classes.
- Reader routes in `service_worker.js` (`READER`) must stay in step with the URLconf.
- The CSS is mobile first and checked by `tests/e2e/test_layout.py` (44 px controls, 16 px form text, WCAG AA contrast
  in both themes, `prefers-reduced-motion`); keep colours in the `--*` variables of `header.css`.

## The song editor

`/add` and `/edit/<pk>` are Bootstrap pages, not part of the reader; `docs/EDITOR.md` describes the template, the
widget, the layout and the script. Rules:

- The template places only the name, the author and the capo; the other fields of `SongForm` come from
  `detail_fields()`, so a new `Song` field needs no template change.
- The preview is the server's (`/markdownx/markdownify/`, `SONG_RENDERER`); never render song markup in JS.
- The lyrics are a vendored prism-code-editor over a real textarea (`highlight.js`), which replaces the textarea when
  `editor.js` loads: listen to the text field on the form, not on the element, and take the patterns of a chord and of
  spaces from `CHORD_RE`/`SPACES_RE` through the textarea's data attributes, never copy them into JS.
- Layout is Bootstrap classes first, with one breakpoint at 1200px; below it the sections are tabs. A `hidden`
  attribute does not beat Bootstrap's `d-flex`: put the flex on an inner element.
- `editor.js` has no catalogue: every string comes from the template. `song.css` is shared with the reader.
- e2e tests stub nothing, not even the Bootstrap CDN.

## Songs payload + caching

`GET /api/songs` returns every song of the tenant as one JSON string, cached per tenant (`{id}-SONGS`,
`{id}-SONGS_archived`); `docs/SONGS_API.md` describes the cache, the delta (`?since=`) and the invalidation. Rules:

- Invalidation is signal-driven (receivers at the bottom of `backend/models.py`); views do **not** invalidate by hand.
  The one exception is `CategoryMoveView`, whose `bulk_update` sends no signals.
- `Song.updated_at` feeds the delta. A bare `update()`/`bulk_update()` that alters a displayed field must call
  `touch_songs()`.
- A `pre_save` receiver refreshes `prerendered` on a full `save()`; `bulk_create` sends no signals, so
  `manage.py import` prerenders before it.
- Tests: the autouse `run_on_commit_at_once` runs `transaction.on_commit` callbacks at once; tests of the deferral use
  `real_on_commit`.

## PDF generation

`PDFTemplate` is a django-polymorphic model and the configuration for a PDF; `Category`, `ManualPDFTemplate` and
`AllSongsTemplate` are its concrete subclasses, each supplying `get_songs()`. Generating creates a `PDFFile` row and
schedules the Huey task `generate_pdf_job`, which runs a file only while it is still `SCHEDULED`.
`docs/FILES.md` describes the template/file workflow and the automatic regeneration, `docs/PDF_LAYOUT.md` the page
layout.

## Container deployment

`Containerfile` builds one image for web and worker, and `deploy/DEPLOY.md` is the guide to the quadlets, nginx and
PostgreSQL. The entrypoint is `make`, so container arguments are Makefile targets (the build bakes in
`compilemessages collectstatic compress_static`, web runs `migrate prerender cache_clear export_static start`, the
worker runs `worker`); keep those targets working without uv (the image sets `RUN` empty). Keep the units free of
quoted arguments in `HealthCmd=`: older quadlet generators drop a closing quote.

## Conventions

- All imports at the top of the file; no inline imports. Signal receivers therefore live in the
  models modules (`backend/models.py`, `tenants/models.py`), not in an `AppConfig.ready()`.
  Where a module needs both `functools.cache` and Django's cache, alias the latter:
  `from django.core.cache import cache as django_cache`.
- Comments and docstrings describe what the code does now — never the previous behaviour, the
  change being made or why it differs from before. That belongs in the commit message.
- Do not add new `_`-prefixed methods unless something genuinely must stay internal; give the
  method a public name, or make it a module-level function. The same goes for reading protected
  members of other objects (`_meta`, `_base_manager`) when a public API exists.
- The reader's strings are English gettext msgids written `_("…")` in `frontend/static/app/*.js` (the name
  `_` is what `xgettext` extracts, so keep it and use literals only). `make messages` extracts them into
  `chords/locale/cs/LC_MESSAGES/djangojs.po`; `frontend/catalogues.py` reads the compiled catalogue and
  `bootstrap_payload` carries it as `i18n`, so both the shell and the server pages translate without a request.
  `make check-messages` (part of `commit-acceptance`) regenerates `djangojs.po` and fails when it differs from
  the committed file or has an untranslated string.
- Every user-visible string goes through `gettext_lazy`/`gettext_noop`. Czech is the default
  language; `make check-messages` also regenerates `chords/locale/cs/LC_MESSAGES/django.po` and fails when it
  differs from the committed file, and `make check-fuzzy` fails the build if either catalogue contains fuzzy
  entries, so run `make messages`, resolve them and commit both files. The catalogues carry no source locations
  (`--no-location`), so they change only when a string or its translation does.
- ruff, line length 120, target `py314` (`.python-version` is 3.14). The `D` (pydocstyle) rules run with the Google
  convention, so every module, package, class, function and method has a docstring: a summary line ending in a period,
  in the descriptive third person (`"""Returns ..."""`; D401 is off), with a blank line before any further text.
  `__init__`, magic methods and nested `Meta` classes are exempt (the class docstring covers them), and migrations
  and the `__init__.py` files of `tests/` are not checked. A method that overrides a framework hook still says what
  it does here.
- Dev dependencies: `uv add --group dev <pkg>`.
- One logical change per commit.
- No fixup commits in the final history: a fix to code a commit of the same branch introduced is
  folded into that commit (`git commit --fixup` + `git rebase --autosquash`), tests included, so
  the branch never contains a commit that repairs an earlier one.
- Conventional Commits for commits and PR titles: `type(scope): summary` — types `feat`, `fix`,
  `perf`, `refactor`, `test`, `docs`, `ci`, `chore`; scopes `backend`, `frontend`, `category`,
  `tenants`, `pdf`, `ci`, `settings`.

## Tests

`tests/README.md` describes the suite: layout, fixtures, settings and the Playwright tests. The `writing-test` skill
lists every fixture with do/don't rules; use it when adding a test. Traps:

- Tests run in Czech against the compiled `.po` files; assert the Czech strings.
- The default tenant is seeded by a migration: `get_or_create` it, and give the test `Client` `HTTP_HOST="localhost"`.
  Look categories up by slug, since the initial migration seeds one too.
- Huey is `immediate`, so a task without a delay renders a real PDF inline: use `mock_weasyprint`, or mark the test
  `slow`.
- `tests/e2e/` is excluded from `make test` (`-m 'not e2e'`); `make e2e` runs it. The client has no JS unit tests, so
  its behaviour is covered there.
