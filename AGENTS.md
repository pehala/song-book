# Project: Chords — Django Songbook

A multi-tenant Django web application serving as an offline-capable songbook (primary use: wilderness/camps with slow internet).

## Tech stack

- **Python 3.14**, **Django 6**, **uv** (package manager)
- **PostgreSQL** in production, **SQLite** in dev/test
- **Redis** for caching (django-redis); `LocMemCache` in tests
- **Huey** for async task queue (PDF generation)
- **WeasyPrint** for PDF rendering
- **nginx** with brotli static pre-compression in production
- **ManifestStaticFilesStorage** with 10-year cache headers for fingerprinted assets

## Running commands

```
uv run python manage.py <command>
uv run --group dev pytest tests/
```

Never use bare `python` — always `uv run`.

## Settings

| Module | Purpose |
|---|---|
| `chords/settings/base.py` | Shared defaults |
| `chords/settings/production.py` | Production overrides (Redis, Postgres) — not committed, generated from `.tpl` |
| `chords/settings/test.py` | Test overrides (LocMemCache, plain StaticFilesStorage, SECRET_KEY, ALLOWED_HOSTS) |

Default `DJANGO_SETTINGS_MODULE` is `chords.settings.production` (requires Redis).  
Tests use `chords.settings.test` — configured in `pyproject.toml` `[tool.pytest.ini_options]`.

## Multi-tenancy

- Each `Tenant` (model in `tenants/`) is identified by `hostname` (unique).
- Middleware (`tenants/middleware.py`) sets `request.tenant` from the hostname on every request; in DEBUG falls back to `Tenant.objects.first()`.
- A data migration (`tenants/migrations/0001_initial.py`) creates a default tenant with `hostname=settings.TENANT_HOSTNAME` (`"localhost"` in base settings) — use `get_or_create` in tests to avoid UNIQUE violations.
- Cache keys are namespaced by tenant: `tenant_cache_key(tenant, key)` → `f"{tenant.id}-{key}"` (from `tenants/utils.py`).

## Key models

| Model | App | Notes |
|---|---|---|
| `Song` | `backend` | `categories` M2M, `archived` bool, `prerendered` TextField |
| `Category` | `category` | `tenant` FK, `slug`, `generate_pdf` |
| `Tenant` | `tenants` | `hostname`, `display_name`, `admins` M2M |

Songs have no direct FK to Tenant — tenant is reached via `song → categories → tenant`.

## Songs caching (improvement 7)

- `SONGS_CACHE_KEY = "SONGS"` in `base.py`
- Cache keys per tenant: `{tenant_id}-SONGS_ALL`, `{tenant_id}-SONGS_ALL_auth`, `{tenant_id}-SONGS_{slug}`, `{tenant_id}-SONGS_{slug}_auth`
- Auth split: superusers see archived songs (separate `_auth` cache key)
- `invalidate_songs_cache(song)` in `backend/utils.py` — iterates `song.categories.all()`, deletes all 4 key variants per category
- `AllSongsJsonView` at `all/data` and `CategorySongsJsonView` at `<slug>/data` serve JSON, populated/read from cache
- Template fetches JSON asynchronously via `fetch("{{ data_url }}")` in an ES module `<script type="module">`

## Static files

- nginx has `brotli_static on` for `/static`; redeploy script pre-compresses with `brotli --quality=11`
- `STATICFILES_STORAGE = ManifestStaticFilesStorage` in production (do **not** use in tests — override with plain `StaticFilesStorage`)

## Tests

```
uv run --group dev pytest tests/ -v
```

Structure:
- `tests/conftest.py` — shared fixtures (`tenant`, `category`, `song`, `anon_client`, `superuser_client`, `staff_client`)
- `tests/test_all_songs_json.py` — `/all/data` endpoint + cache behaviour
- `tests/test_category_songs_json.py` — `/<slug>/data` endpoint
- `tests/test_cache_invalidation.py` — `invalidate_songs_cache` utility

## Conventions

- No inline imports — all imports at top of file
- Each logical change in a separate git commit
- Tests in a separate commit
- `uv add --group dev <pkg>` for dev dependencies
- `backend/utils.py` imports `functools.cache` (stdlib) — Django cache must be aliased: `from django.core.cache import cache as django_cache`

## Commit message format

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <short summary>
```

Common types:

| Type | When to use |
|---|---|
| `feat` | New feature or behaviour |
| `fix` | Bug fix |
| `perf` | Performance improvement (no behaviour change) |
| `refactor` | Code restructure (no behaviour change, not a fix) |
| `test` | Adding or updating tests only |
| `docs` | Documentation only (README, AGENTS.md, comments) |
| `ci` | CI/CD config (GitHub Actions, Makefile targets) |
| `chore` | Maintenance (deps, tooling, config) |

Common scopes: `backend`, `frontend`, `category`, `tenants`, `pdf`, `ci`.  
Scope is optional for changes that span the whole project.

Examples:
- `feat(backend): add songs JSON endpoints with Redis caching`
- `fix(frontend): fix crash in error template when tenant has no icon`
- `perf(frontend): fetch songs JSON async instead of embedding in HTML`
- `test: add pytest suite for songs JSON endpoints and cache invalidation`
- `ci: add make test target and GitHub Actions test step`

## Active branch

`separate-songs-load` — improvement 7 (separate songs JSON endpoint with Redis caching).
