"""Invalidation of the songs payload kept in the cache"""

from functools import partial

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from tenants.utils import tenant_cache_key


def songs_payload_key(tenant, include_archived):
    """Cache key of the combined songs payload of a tenant"""
    key = tenant_cache_key(tenant, settings.SONGS_CACHE_KEY)
    return f"{key}_archived" if include_archived else key


def invalidate_tenant_songs_cache(tenant):
    """
    Invalidates the combined songs payload of a tenant, in both its public and its archived variant.

    Inside a transaction this waits for the commit: a list rebuilt before it would read the old rows
    and keep them in the cache.
    """
    keys = [songs_payload_key(tenant, include_archived) for include_archived in (False, True)]
    transaction.on_commit(partial(cache.delete_many, keys))


def song_tenants(song):
    """Tenants whose song lists contain the song"""
    return {category.tenant for category in song.categories.select_related("tenant")}


def invalidate_songs_cache(song):
    """Invalidates the songs payload of every tenant the song belongs to"""
    for tenant in song_tenants(song):
        invalidate_tenant_songs_cache(tenant)


def touch_songs(songs):
    """Marks the songs of the queryset as changed, for the readers that fetch only what changed since their copy"""
    songs.update(updated_at=timezone.now())
