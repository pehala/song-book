"""Builds the songs payload served to the browser and keeps it in the cache."""

import json
from collections.abc import Callable, Iterable
from datetime import UTC, datetime

from django.conf import settings
from django.core.cache import cache
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Prefetch, QuerySet
from django.forms import model_to_dict

from backend.cache import songs_payload_key
from backend.models import Song
from category.models import Category


def transform_song(song: Song, number: int) -> dict:
    """Transforms song into a dict; its categories must be prefetched into `tenant_categories`."""
    transformed = model_to_dict(song, ["id", "name", "capo", "author", "link", "archived"])
    transformed["number"] = number
    transformed["cats"] = [category.slug for category in song.tenant_categories]
    transformed["text"] = song.rendered_markdown
    return transformed


def visible_songs(queryset: QuerySet, include_archived: bool) -> QuerySet:
    """Restricts queryset to songs the current user may see."""
    if include_archived:
        return queryset
    return queryset.filter(archived=False)


def songs_to_json(songs: Iterable[Song]) -> str:
    """Serializes songs into the JSON list consumed by the reader.

    Songs are numbered 1..N in queryset order; archived songs are moved to the end
    and keep counting, so numbers are stable for the public part of the list.
    """
    result = []
    archived = []

    number = 1
    for song in songs:
        if song.archived:
            archived.append(song)
            continue
        result.append(transform_song(song, number))
        number += 1

    for song in archived:
        result.append(transform_song(song, number))
        number += 1

    return json.dumps(result, cls=DjangoJSONEncoder)


def tenant_songs(tenant, include_archived: bool) -> QuerySet:
    """Songs of the tenant the user may see, each with its tenant's categories prefetched."""
    songs = (
        Song.objects.filter(categories__tenant=tenant)
        .distinct()
        .prefetch_related(
            Prefetch("categories", queryset=Category.objects.filter(tenant=tenant), to_attr="tenant_categories")
        )
    )
    return visible_songs(songs, include_archived)


def build_songs_payload(tenant, include_archived: bool) -> str:
    """Serializes every song of the tenant together with the slugs of the tenant's categories it is in."""
    return songs_to_json(tenant_songs(tenant, include_archived))


def build_songs_delta(tenant, include_archived: bool, since: int, etag: str) -> str:
    """Serializes what a reader holding the list as of `since` (epoch seconds) is missing.

    `ids` names every current song in list order, which is also what numbers them, so the reader drops
    the songs that are gone, renumbers by position and takes the rows of `changed`, the songs edited
    at or after `since`. `etag` is the one of the full list, which the merged list answers to from then on.
    """
    songs = tenant_songs(tenant, include_archived)
    listed = list(songs.values_list("id", "archived"))
    ids = [pk for pk, archived in listed if not archived] + [pk for pk, archived in listed if archived]
    numbers = {pk: number for number, pk in enumerate(ids, start=1)}
    changed = songs.filter(pk__in=ids, updated_at__gte=datetime.fromtimestamp(since, UTC))
    return json.dumps(
        {
            "etag": etag,
            "now": int(datetime.now(UTC).timestamp()),
            "ids": ids,
            "changed": [transform_song(song, numbers[song.id]) for song in changed],
        },
        cls=DjangoJSONEncoder,
    )


def cached_songs_payload(tenant, include_archived: bool) -> str:
    """Returns the combined songs payload of the tenant from the cache, building it on a miss."""
    return cached_json(
        songs_payload_key(tenant, include_archived), lambda: build_songs_payload(tenant, include_archived)
    )


def cached_json(key: str, build: Callable[[], str]) -> str:
    """Returns the JSON string stored under key, building and storing it only on a cache miss."""
    cached = cache.get(key)
    if cached is None:
        cached = build()
        cache.set(key, cached, settings.CACHE_TIMEOUT)
    return cached
