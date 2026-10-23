"""Builds the songs JSON payloads served to the browser and keeps them in the cache"""

import json
from collections.abc import Callable, Iterable

from django.conf import settings
from django.core.cache import cache
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import QuerySet
from django.forms import model_to_dict

from backend.models import Song


def transform_song(song: Song, number: int) -> dict:
    """Transforms song into a dict representation"""
    transformed = model_to_dict(song, ["id", "name", "capo", "author", "link", "archived"])
    transformed["number"] = number
    transformed["text"] = song.rendered_markdown
    return transformed


def visible_songs(queryset: QuerySet, include_archived: bool) -> QuerySet:
    """Restricts queryset to songs the current user may see"""
    if include_archived:
        return queryset
    return queryset.filter(archived=False)


def songs_to_json(songs: Iterable[Song]) -> str:
    """
    Serializes songs into the JSON list consumed by the song list page.

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


def cached_json(key: str, build: Callable[[], str]) -> str:
    """Returns the JSON string stored under key, building and storing it only on a cache miss"""
    cached = cache.get(key)
    if cached is None:
        cached = build()
        cache.set(key, cached, settings.CACHE_TIMEOUT)
    return cached
