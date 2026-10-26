# Songs payload and caching

`GET /api/songs` (`SongsApiView`, `chords:songs_api`) returns every song of the tenant as one JSON list with the slugs
of its categories in `cats`. The browser filters it per route and numbers the list itself (non-archived songs first,
archived ones appended).

## Building and caching

- The view looks the JSON **string** up in the cache first and only on a miss builds it through `backend/songs.py`
  (`cached_songs_payload` → `build_songs_payload` → `songs_to_json`, with a tenant-filtered `Prefetch` of the
  categories). A hit or a 304 costs one cache read. `transform_song()` fixes the field order of each row.
- Cache keys per tenant: `{id}-SONGS` and `{id}-SONGS_archived` (`songs_payload_key`). The `_archived` variant is
  chosen by `is_superuser`, the only users who see archived songs, and is served `private`; tenant admins share the
  public entry.
- `ETagJsonMixin` hashes the cached JSON (blake2b) into an ETag and returns 304 via `get_conditional_response`, with
  `Cache-Control: no-cache`.

## Invalidation

Invalidation is signal-driven. The receivers at the bottom of `backend/models.py` clear both variants for the affected
tenants on:

- `Song` save and delete;
- `Song.categories` membership changes, captured on `pre_remove`/`pre_clear` so the old categories are covered, and
  cleared again on `post_remove`/`post_clear`;
- `Category` save and delete, including the previous tenant, plus the `CATEGORY_CACHE_KEY` menu entry.

The helpers are in `backend/cache.py`: `invalidate_tenant_songs_cache(tenant)` and the per-song wrapper
`invalidate_songs_cache(song)`. Invalidation inside a transaction (the Django admin saves in `atomic()`) waits for the
commit through `transaction.on_commit`; the tests' autouse `run_on_commit_at_once` runs those callbacks at once, and
tests of the deferral use `real_on_commit`.

Views do **not** invalidate by hand. The one exception is `CategoryMoveView`, whose `bulk_update` sends no signals.

A `pre_save` receiver refreshes `prerendered` on every full `save()` while `USE_PRERENDERED_MARKDOWN` is on (a save with
`update_fields` skips it), so admin edits and scripts cannot leave it stale. `bulk_create` sends no signals, so
`manage.py import` prerenders before it.

## Delta

`GET /api/songs?since=<epoch seconds>` with the stored ETag in `If-None-Match` answers a 304 when the list is current
and otherwise `{etag, now, ids, changed}` (`build_songs_delta`, `no-store`): `ids` is every visible song in list order,
which numbers them, and `changed` the full rows with `Song.updated_at >= since`.

`updated_at` is bumped by `auto_now`, which only a `save()` triggers, and by `touch_songs()` wherever rows change
without one: category membership changes, category save and delete, `CategoryMoveView` and `manage.py prerender`. Any
other `update()`/`bulk_update()` that alters a displayed field must call it too.

`store.js` (`mergeDelta`) merges the delta into the stored list, asking from 60 s before the stored copy's `Date`, and
falls back to the whole list when the delta does not fit. The shell therefore does not `preload` `/api/songs`.

## Progress

Both response kinds carry the uncompressed byte length in `X-Songs-Size`. `store.js` reads the body in chunks and
reports `{loaded, total}`, which `app.js` draws as a progress bar while no list is stored and as a thin line along the
top while a stored list is being brought up to date (hidden for the first 300 ms).
