# Tests

`tests/` is a pytest-django suite split per app (`backend/`, `category/`, `pdf/`, `tenants/`, `chords/`, `analytics/`,
`frontend/`), plus two suite-wide modules: `test_url_permissions.py`, a parametrized matrix asserting login redirect,
403 and allowed access for every URL in the project, and `test_menus.py`. Each directory is a package: the `__init__.py`
files are what keep same-named modules such as `backend/test_models.py` and `category/test_models.py` from colliding.

## Fixtures

`conftest.py` provides the shared fixtures: `tenant`/`other_tenant`, `category`, `song`, `archived_song`, the
`make_category`/`make_song`/`make_pdf_file` factories, `manual_template`, `pdf_file`, `superuser`/`staff_user`/`plain_user` and the
matching `Client` fixtures.

- Three autouse fixtures clear the cache, flush the task queue and point `MEDIA_ROOT` at a `tmp_path`, so generated PDFs
  and uploads never reach the source tree.
- The session-scoped autouse `compiled_messages` compiles the `.po` files with `msgfmt` into a temporary directory and
  points `LOCALE_PATHS` there, so the tests run in the default language (Czech) with real translations whatever `.mo`
  files lie in the source tree. Assert the Czech strings.
- `run_on_commit_at_once` (autouse) runs `transaction.on_commit` callbacks at once; tests of the deferral use
  `real_on_commit`.
- `pdf/conftest.py` adds the PDF-only fixtures. Fixtures used by a single module live in that module.
- The initial migration already seeds a category for the default tenant, so tests look categories up by slug rather than
  assume the fixture is the only one.

`backend/test_signals.py` covers the signal-driven invalidation and prerender-on-save; `chords/test_storage.py` runs a
real `collectstatic` into a `tmp_path` to check that hashed modules import hashed modules.

## Settings

The suite runs on SQLite against `chords.settings.test`; production uses PostgreSQL and Redis, so anything cache- or
tenant-related is exercised through LocMemCache here.

- Huey runs with `immediate=True`, so a task scheduled without a delay renders inline. Tests that do not want a real PDF
  use the `mock_weasyprint` fixture, and the few that do are marked `slow` (`pytest -m "not slow"` skips them).
- Passwords are hashed with MD5: the default PBKDF2 hasher costs ~200 ms per user and the tests sign in with
  `force_login()`.

## End to end

`e2e/` drives the reader in Chromium through Playwright (pytest-playwright against pytest-django's `live_server`) and is
excluded from the default run by `addopts = "-m 'not e2e'"`; `make e2e` runs it. There is no JS unit test runner:
behaviour of the client is covered here.

- The `library` fixture builds a two-category songbook and `sign_in(user)` puts a session cookie into the browser.
- The browser is pinned to `en-US` (`browser_context_args`), so the reader is English there until a test switches the
  language.
- `DJANGO_ALLOW_ASYNC_UNSAFE` is set so the test thread can use the ORM next to Playwright's event loop. The live server
  shares one in-memory SQLite database, so wait for the page to go idle before writing from the test.
- The song editor's tests are the package `e2e/editor/`: `conftest.py` has the `editor` fixture (the editor of a song on a
  phone), `helpers.py` what the modules share, and each module one part of the page (layout, keys, changes, splitter,
  details).

## Coverage

Coverage is configured in `pyproject.toml` (branch coverage; migrations, `apps.py`, `wsgi.py`, the uncommitted
`production.py` and the env-driven `container.py` omitted); `make coverage` reports it.
