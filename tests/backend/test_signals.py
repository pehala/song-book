"""Tests for signal-driven cache invalidation and prerendering on save."""

import json

import pytest
from django.conf import settings
from django.core.cache import cache
from django.db.models.signals import m2m_changed
from django.test import override_settings
from django.urls import reverse

from backend.cache import songs_payload_key
from backend.models import Song
from category.models import Category
from chords.settings.base import CATEGORY_CACHE_KEY
from tenants.models import Tenant
from tenants.utils import tenant_cache_key

pytestmark = pytest.mark.django_db

URL = reverse("chords:songs_api")


def payload_key(tenant):
    """The cache key of the public songs payload of the tenant."""
    return songs_payload_key(tenant, False)


def prime_payload(client):
    """Requests the songs so that their payload lands in the cache."""
    client.get(URL)


def songs(client):
    """Returns the songs the API lists for the client, by name."""
    return {entry["name"]: entry for entry in json.loads(client.get(URL).content)}


@pytest.fixture
def primed(anon_client, song):
    """The song, with the payload that lists it in the cache."""
    prime_payload(anon_client)
    return song


def assert_rebuilt(client, tenant, names):
    """Asserts that the cached payload was dropped and the next one lists the songs of the given names."""
    assert cache.get(payload_key(tenant)) is None
    assert set(songs(client)) == names


def test_song_save_clears_the_payload(anon_client, primed, tenant):
    """Saving a song, as the admin does, clears the payload without any explicit call."""
    primed.name = "Renamed"
    primed.save()

    assert_rebuilt(anon_client, tenant, {"Renamed"})


def test_song_delete_clears_the_payload(anon_client, primed, tenant):
    """Deleting a song clears the payload of the tenants it belonged to."""
    primed.delete()

    assert_rebuilt(anon_client, tenant, set())


def test_clearing_the_categories_clears_the_payload(anon_client, primed, tenant):
    """A song taken out of every category leaves the payload."""
    primed.categories.clear()

    assert_rebuilt(anon_client, tenant, set())


def test_new_song_added_to_a_category_clears_the_payload(anon_client, primed, tenant, category):
    """A song created and linked to a category appears on the next request."""
    Song.objects.create(name="Late", text="y").categories.add(category)

    assert_rebuilt(anon_client, tenant, {"Test Song", "Late"})


def test_category_gaining_a_song_clears_the_payload(anon_client, primed, tenant, category):
    """Adding a song from the category's side clears the payload too."""
    category.song_set.add(Song.objects.create(name="Late", text="y"))

    assert_rebuilt(anon_client, tenant, {"Test Song", "Late"})


def test_removing_category_updates_cats(anon_client, song, tenant, category):
    """Removing a song from a category is visible in the next payload, which the cached one would hide."""
    other = Category.objects.create(tenant=tenant, name="Other", slug="other", generate_pdf=False)
    song.categories.add(other)
    prime_payload(anon_client)
    song.categories.remove(category)
    assert cache.get(payload_key(tenant)) is None
    assert songs(anon_client)["Test Song"]["cats"] == ["other"]


def test_category_rename_clears_payload_and_menu(anon_client, song, tenant, category):
    """Renaming a slug clears the payload, whose `cats` name it, and the category menu."""
    prime_payload(anon_client)
    cache.set(tenant_cache_key(tenant, CATEGORY_CACHE_KEY), ["menu"])
    category.slug = "renamed"
    category.save()
    assert cache.get(payload_key(tenant)) is None
    assert cache.get(tenant_cache_key(tenant, CATEGORY_CACHE_KEY)) is None
    assert songs(anon_client)["Test Song"]["cats"] == ["renamed"]


def test_category_create_clears_the_menu(tenant, make_category):
    """A new category has to show up in the navigation."""
    cache.set(tenant_cache_key(tenant, CATEGORY_CACHE_KEY), ["menu"])

    make_category(tenant, name="Created", slug="created")

    assert cache.get(tenant_cache_key(tenant, CATEGORY_CACHE_KEY)) is None


def test_category_delete_clears_payload_and_menu(anon_client, song, tenant, category):
    """Deleting a category clears the payload and the category menu."""
    prime_payload(anon_client)
    cache.set(tenant_cache_key(tenant, CATEGORY_CACHE_KEY), ["menu"])
    category.delete()
    assert cache.get(payload_key(tenant)) is None
    assert cache.get(tenant_cache_key(tenant, CATEGORY_CACHE_KEY)) is None


def test_category_move_clears_both_tenants(anon_client, song, tenant, category):
    """Moving a category to another tenant clears the payload and menu of the old and the new tenant."""
    other_tenant = Tenant.objects.create(hostname="other.localhost", name="Other", display_name="Other")
    prime_payload(anon_client)
    cache.set(payload_key(other_tenant), "[]")
    cache.set(tenant_cache_key(tenant, CATEGORY_CACHE_KEY), ["menu"])
    cache.set(tenant_cache_key(other_tenant, CATEGORY_CACHE_KEY), ["menu"])
    category.tenant = other_tenant
    category.save()
    assert cache.get(payload_key(tenant)) is None
    assert cache.get(payload_key(other_tenant)) is None
    assert cache.get(tenant_cache_key(tenant, CATEGORY_CACHE_KEY)) is None
    assert cache.get(tenant_cache_key(other_tenant, CATEGORY_CACHE_KEY)) is None


def test_other_tenant_untouched(anon_client, song, tenant):
    """Edits in one tenant leave another tenant's cached payload alone."""
    other_tenant = Tenant.objects.create(hostname="other.localhost", name="Other", display_name="Other")
    cache.set(payload_key(other_tenant), "[]")
    prime_payload(anon_client)
    song.save()
    assert cache.get(payload_key(other_tenant)) == "[]"


@override_settings(USE_PRERENDERED_MARKDOWN=True)
def test_save_prerenders_when_enabled(category):
    """With prerendering on, every save fills the prerendered column from the text."""
    song = Song.objects.create(name="Pre", text="{Ami}Hello")
    assert '<rt class="chord">Ami</rt>' in song.prerendered
    song.text = "{C}Changed"
    song.save()
    song.refresh_from_db()
    assert '<rt class="chord">C</rt>' in song.prerendered
    assert "Ami" not in song.prerendered


@override_settings(USE_PRERENDERED_MARKDOWN=True)
def test_update_fields_without_text_keeps_prerendered(category):
    """A save restricted to other fields does not re-render the text."""
    song = Song.objects.create(name="Pre", text="{Ami}Hello")
    song.text = "{C}Changed"
    song.save(update_fields=["name"])
    song.refresh_from_db()
    assert "Ami" in song.prerendered


def test_save_leaves_prerendered_alone_when_disabled(category):
    """With prerendering off (the default in tests) the column stays untouched."""
    assert settings.USE_PRERENDERED_MARKDOWN is False
    song = Song.objects.create(name="Pre", text="{Ami}Hello")
    assert song.prerendered is None


@pytest.mark.parametrize("change", ["remove", "clear"])
def test_list_rebuilt_before_the_membership_change_is_dropped_after_it(anon_client, song, tenant, category, change):
    """A request between the invalidation and the change caches the old links, so the change invalidates again."""

    def rebuild_in_between(sender, action, **kwargs):
        if action.startswith("pre_"):
            prime_payload(anon_client)

    m2m_changed.connect(rebuild_in_between, sender=Song.categories.through)
    try:
        if change == "remove":
            song.categories.remove(category)
        else:
            song.categories.clear()
    finally:
        m2m_changed.disconnect(rebuild_in_between, sender=Song.categories.through)

    assert cache.get(payload_key(tenant)) is None


def test_invalidation_inside_a_transaction_waits_for_the_commit(
    anon_client, song, tenant, real_on_commit, django_capture_on_commit_callbacks
):
    """The Django admin saves inside atomic(); a list rebuilt before the commit would keep the old rows."""
    prime_payload(anon_client)

    with django_capture_on_commit_callbacks() as callbacks:
        song.name = "Renamed"
        song.save()
        assert cache.get(payload_key(tenant)) is not None

    assert callbacks
    for callback in callbacks:
        callback()
    assert cache.get(payload_key(tenant)) is None


def test_category_menu_invalidation_waits_for_the_commit(
    category, tenant, real_on_commit, django_capture_on_commit_callbacks
):
    """Saving a category drops its menu from the cache only once the transaction has committed."""
    key = tenant_cache_key(tenant, CATEGORY_CACHE_KEY)
    cache.set(key, "menu")

    with django_capture_on_commit_callbacks() as callbacks:
        category.name = "Renamed"
        category.save()
        assert cache.get(key) == "menu"

    for callback in callbacks:
        callback()
    assert cache.get(key) is None
