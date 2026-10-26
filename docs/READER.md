# The reader

The reader (song list, search, category switching, song view) is a Preact + htm single page app with no build step.
Everything else (CRUD, PDF, analytics, login, `/admin/`) keeps its Django templates and Bootstrap from the CDN.

## Modules

The modules are in `frontend/static/app/`:

- `app.js`: the reader's entry; `site.js`: the entry for server pages
- `header.js`, `options.js`, `songs.js`, `store.js`, `i18n.js`
- `page.js` and the page entries (`progress.js`, `analytics.js`)
- `vendor/preact-htm.module.js`, `vendor/qr.mjs`
- `header.css`, `app.css`

They are listed once in `frontend.views` (`MODULES`, `SITE_ENTRY`, `PAGE_ENTRIES`/`PAGE_MODULES`, `STYLESHEETS`), which
feeds the preload links and the service worker's precache. A new file must be added there. Keep modules free of import
cycles (hashing needs a DAG) and `import()` out of modules with nested template literals: `ManifestStorage` cannot see
past them.

## The shell

`ShellView` serves **one** page, `frontend/templates/shell.html`, for `/`, `/all` and `/categories/<slug>`: the
stylesheets as `<link>`s (`STYLESHEETS`), an SVG sprite, `modulepreload` links and the tenant's bootstrap JSON in
`<script id="boot">` (`tenants/bootstrap.py: bootstrap_payload`, built from the entries the navigation menus keep in the
cache, so menu invalidation covers it). It does not `preload` `/api/songs`; see `docs/SONGS_API.md`.

The shell reads no user, session, message, CSRF or language, so there is no `Vary: Cookie`; it gets an ETag and
`Cache-Control: no-cache`. An unknown category slug gets the same body with status 404. Keep it that way: the service
worker serves one cached copy to every route and every user. `RecognizeTenantMiddleware` resolves `is_localadmin`
lazily for the same reason.

## The header

The header (`header.js`: `SiteHeader`, which draws the bar, the notices and the QR dialog from the state of
`useSiteHeader`) is one Preact component used twice: by the reader and, through `site.js`, by every Bootstrap page.

- `base/index.html` has an empty `#site-header`, the `boot` and `me` JSON (from `frontend.context_processors.header`,
  evaluated only when printed) and loads `site.js`. A menu entry is added in `header.js` only.
- Header markup and `header.css` use `sb-` prefixed classes so they cannot clash with Bootstrap.
- The theme is the `data-bs-theme` attribute on `<html>` (set early by an inline script, then by `options.js`), which
  both Bootstrap and the reader's CSS follow.
- Pages the server renders (`server: true`) take their language from `<html lang>`, change it by POSTing `setlang` and
  reloading, and leave out the options that need songs.

## Server pages drawn by Preact

Some Bootstrap pages have their content drawn by Preact too: the template keeps the title, renders an empty `#page` and
the page's data as `page-data` JSON and loads a page entry (`progress.js` for `/pdf/files/wait/<pk>`, `analytics.js`
for `/analytics/`), which calls `mountPage` from `page.js`. The data names the JSON endpoints the page calls, and the
strings are `_("…")` msgids of the reader's catalogue, translated into the language of `<html lang>`.

## CSS

The CSS is mobile first (`min-width` queries), every control is at least 44 px, form fields use 16 px text, text meets
WCAG AA contrast in both themes and animations stop under `prefers-reduced-motion`. `tests/e2e/test_layout.py` checks
all of it, so keep colours in the `--*` variables of `header.css`.

## The user and the client state

- `/api/me` (`MeView`) is the only place that knows the user: `auth`, `username`, `localadmin`, `superuser`, plus the
  pending `django.contrib.messages`, which it drains; the CRUD views still redirect to the shell and the toast arrives
  through here. It is `private, no-store` and sets the CSRF cookie.
- The client keeps UI options in `localStorage` (`theme`, `lang`, `columns`, `hide_chords`, `prevent_sleep`; `theme`
  keeps the key the Bootstrap pages use) and fetches songs through `store.js` (Cache API entry `songs`: draw the stored
  list, revalidate, replace it when the ETag changed; deleted on logout).
- Statistics are counted by the server: each `/api/songs` request, which the reader makes once per open, adds a hit
  under the key `all`.

## Service worker

`ServiceWorkerView` renders `frontend/templates/service_worker.js` per tenant:

- the cache name hashes the precached urls and carries the tenant id;
- the shell is cache-first with background ETag revalidation (`ignoreVary`);
- `/static/*`, the manifest and the logo are cache-first;
- everything else (including `/api/*`) goes to the network.

A new worker waits; the page shows a toast and sends `skipWaiting`. Reader routes in `service_worker.js` (`READER`)
must stay in step with the URLconf.
