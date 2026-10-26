---
name: writing-test
description: How to write a test for this songbook project - which fixtures exist (root, pdf, e2e, migrations), what each gives you, and the do/don't list. Use whenever you add or change a test under tests/, or write code that needs one.
---

# Writing a test

Run tests through `uv`, never bare `pytest`:

```bash
uv run --group dev pytest tests/backend/test_etag.py::test_response_has_etag -v
uv run --group dev pytest tests/ -m "not slow and not e2e"
make e2e        # tests/e2e/ only, needs Chromium
```

## Where it goes

- One directory per app: `tests/backend/`, `category/`, `pdf/`, `tenants/`, `chords/`, `analytics/`, `frontend/`.
  Name the module `test_<what>.py`; every directory is a package (`__init__.py`), so same-named modules do not collide.
- Suite-wide matrices live in `tests/test_url_permissions.py` (every URL: login redirect, 403, allowed) and
  `tests/test_menus.py`. A new URL gets a row in the permissions matrix.
- Browser tests of the reader go in `tests/e2e/`; tests of data migrations in `tests/migrations/<app>/`.
- A fixture used by one module lives in that module; one used by a directory goes into its `conftest.py`.

A test module starts like this (the module docstring, `pytestmark` and `reverse()` are the house style):

```python
"""Tests for ETag-based client-side caching on the songs payload."""

import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db

URL = reverse("chords:songs_api")

def test_304_on_matching_etag(anon_client, song):
    """Second request with matching If-None-Match returns 304 Not Modified."""
    etag = anon_client.get(URL)["ETag"]

    assert anon_client.get(URL, HTTP_IF_NONE_MATCH=etag).status_code == 304
```

## Fixtures

### Autouse (you get them without asking)

| Fixture | Effect |
|---|---|
| `compiled_messages` (session) | Compiles the `.po` files with `msgfmt` into a temp dir and points `LOCALE_PATHS` there: tests run in **Czech** with real translations whatever `.mo` files lie in the tree |
| `run_on_commit_at_once` | Replaces `transaction.on_commit` so callbacks run immediately (the test transaction never commits) |
| `clear_cache` | Empties the cache before and after each test |
| `flush_huey` | Flushes the Huey queue before and after each test |
| `media_root` | Points `MEDIA_ROOT` at `tmp_path` and returns it |

### Opt in: root `tests/conftest.py`

| Fixture | Gives you |
|---|---|
| `real_on_commit` | Restores the real `on_commit` deferral, for tests of what waits for a commit |
| `tenant` | The default tenant (`hostname="localhost"`), `get_or_create`d because the initial migration seeds it |
| `other_tenant` | A second tenant (`other.localhost`), to prove data does not leak between tenants |
| `make_category` | Factory `make_category(tenant, **kwargs)`; defaults: name `Test Category`, slug `test-cat`, `generate_pdf=False`, filename `songbook`, locale `en` |
| `category` | `make_category(tenant)` |
| `other_category` | A category of `other_tenant` (slug `other-cat`) |
| `make_song` | Factory `make_song(*categories, **kwargs)`; defaults: name `Test Song`, text `{Ami}Hello {C}World`; adds the categories |
| `song` | A song in `category` |
| `archived_song` | An archived song in `category` |
| `manual_template` | A `ManualPDFTemplate` of the tenant, without songs |
| `all_songs_template` | The tenant's `AllSongsTemplate` with `generate_pdf=True` |
| `make_pdf_file` | Factory `make_pdf_file(template=None, *, file=None, content=None, **kwargs)`: a `QUEUED` `PDFFile` of the template (and its tenant), or of the default tenant without one; `file` sets a storage path without touching disk, `content` writes real bytes |
| `pdf_file` | A `QUEUED` `PDFFile` created from `category` |
| `development_stylesheet` | `DEBUG = True`, with the header stylesheet served from a copy in `tmp_path` that the test can edit |
| `superuser`, `staff_user`, `plain_user` | A superuser; a user in `tenant.admins` (local admin); a user without rights |
| `anon_client` | `Client(HTTP_HOST="localhost")`, not signed in |
| `superuser_client`, `staff_client`, `plain_client` | The same client, signed in with `force_login()` as the matching user |

### Opt in: `tests/pdf/conftest.py` (only inside `tests/pdf/`)

| Fixture | Gives you |
|---|---|
| `pdf_category` | A category with `generate_pdf=True`, slug `pdf-cat`, filename `test-cat` |
| `pdf_song` | A non-archived song in `pdf_category` |
| `pdf_song_entry` | A `PDFSong` linking `pdf_song` into the root `manual_template` as number 1 |
| `mock_weasyprint` | Patches `pdf.generate.weasyprint.HTML`; `write_pdf()` writes `b"%PDF-fake"`. Yields the mocked class |

### Opt in: `tests/e2e/conftest.py` (only inside `tests/e2e/`, marked `e2e` automatically)

| Fixture | Gives you |
|---|---|
| `base_url` | The live server's URL, so `page.goto("/categories/cs")` resolves |
| `browser_context_args` | Pins the browser locale to `en-US`: the reader is English there until a test switches the language |
| `library` | A two-category songbook (`cs` "Česky" and `en` "English"), a song in both, `index_redirect="/categories/cs"` |
| `sign_in` | `sign_in(user)` puts a session cookie for `user` into the browser |
| `requests_made` | Every `(method, url)` the page makes, as a list |
| `offline_cdn` | Fulfils `https://cdn.jsdelivr.net/**` with an empty body so server pages do not wait for Bootstrap; request it with `pytestmark = pytest.mark.usefixtures("offline_cdn")` |
| `hold` | `hold(pattern)` holds the requests to a URL pattern until the test continues them and returns the list of held routes |
| `poll` | `poll(condition)` waits up to five seconds for a condition `wait_for_function` cannot check (a cookie, or a page whose CSP forbids eval) |
| `page`, `context` | From pytest-playwright |

### Opt in: `tests/migrations/conftest.py` (module-scoped)

A module overrides `migration_target` (the `(source, target)` pairs, each `(app, name)`) and `create_old_data`; the
fixtures `migration_connection`, `schema`, `migrate`, `rows("app.Model")`, `migrate_to_start` and the autouse
`migrate_to_end` run the real migrations against a scratch in-memory database. Insert old rows through the models of
the source state that `rows` gives, never the current models.

### Marks

`django_db` (via `pytestmark`), `parametrize`, `slow` (a real WeasyPrint render; deselect with `-m "not slow"`), `e2e`
(added automatically under `tests/e2e/`; excluded from the default run by `addopts`).

## Do

- Put `pytestmark = pytest.mark.django_db` at module level (a fixture that needs `db` also works).
- Request the most specific fixture: `anon_client`/`staff_client`/... instead of building a `Client`; `make_song` and
  `make_category` instead of `Song.objects.create(...)` by hand.
- Build URLs with `reverse(...)`; the URL name is the contract, the path is not.
- Assert the **Czech** strings (the default language). Only e2e tests see English.
- Give every test and fixture a docstring: a summary line ending in a period, in the descriptive third person. Ruff's
  `D` rules (Google convention) apply to `tests/`; only `__init__.py` files and migrations are exempt.
- Keep all imports at the top of the file; no inline imports.
- Test tenant isolation whenever data is tenant-scoped: add `other_tenant`/`other_category` and assert nothing leaks.
- Look categories up by slug (`Category.objects.get(slug=...)`): the initial migration seeds one for the default
  tenant, so `category` is never the only one.
- Test cache invalidation through the signals: save/delete the model and assert the effect (see
  `tests/backend/test_signals.py`). Use `real_on_commit` only when the test is about the deferral itself.
- Use `mock_weasyprint` for anything that generates a PDF. Huey is `immediate` in the tests, so a task scheduled without
  a delay renders inline; a test that really needs WeasyPrint is marked `slow`.
- Use `@pytest.mark.parametrize` for a matrix of inputs instead of copy-pasted tests or a loop in the test body: each
  case then passes or fails on its own.
- Parametrize with plain data (strings, numbers, classes, names) and give each case a readable `id` through
  `pytest.param(..., id="...")`, as `tests/backend/test_auth.py` does.
- A case that needs a fixture (a user, a client, a song) names it as a string and the test resolves it with
  `request.getfixturevalue(name)`; fixtures cannot be parametrize arguments themselves.
- Use `monkeypatch` and `settings` for changes to settings and attributes so they are undone for you.
- Cover every branch of what you add: coverage is branch coverage, checked with `make coverage`.
- Fold the tests into the commit of the code they cover; there are no separate `test:` commits for new code.
- In e2e tests, wait on the page (`expect(...).to_be_visible()`, `page.wait_for_*`) and let it go idle before writing
  to the database from the test: the live server shares one in-memory SQLite database. Keep colours and sizes under
  the checks of `tests/e2e/test_layout.py`.

## Don't

- Don't run bare `python` or `pytest`; use `uv run --group dev pytest ...` or `make test`.
- Don't `Tenant.objects.create(hostname="localhost")`: it violates the unique constraint. Use the `tenant` fixture.
- Don't build `Client()` without `HTTP_HOST="localhost"`: the tenant middleware 404s an unknown host.
- Don't assert English UI strings outside e2e, and don't hard-code a `.mo` file.
- Don't invalidate caches by hand in a test to make it pass; if invalidation is missing, that is a bug in the code.
- Don't use `ManifestStorage` in tests: no manifest is collected. Only `tests/chords/test_storage.py` runs a real
  `collectstatic`, into a `tmp_path`.
- Don't let a test write into the source tree: uploads and PDFs go to `media_root`, any other file to `tmp_path`.
- Don't render a real PDF without the `slow` mark.
- Don't use `time.sleep` in e2e tests, and don't write to the database from the test while the page is still loading.
- Don't test the client's behaviour with a JS runner: there is none; it is covered by `tests/e2e/`.
- Don't put a lambda in a parametrization (neither as a value nor as `ids=`): its id is unreadable (`<lambda>`), and it
  hides what the case does. Pass data and let the test act on it, or give the case a named module-level function.
- Don't add `_`-prefixed helpers or read `_meta`/`_base_manager`; use the public API, in tests as everywhere.
- Don't commit a test together with a fix to code the same branch introduced in another commit: fold both into that
  commit (`git commit --fixup` + `git rebase --autosquash`).
