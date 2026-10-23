"""Tests for creating, updating and deleting songs."""

import json

import pytest
from django.conf import settings
from django.core.cache import cache
from django.urls import reverse

from backend.models import Song
from pdf.models.request import PDFFile
from tenants.utils import tenant_cache_key

pytestmark = pytest.mark.django_db

ALL_SONGS_KEY = f"{settings.SONGS_CACHE_KEY}_ALL"


def pending_messages(client):
    """The messages the reader receives from /api/me after the redirect"""
    return json.loads(client.get(reverse("chords:me")).content)["messages"]


def song_payload(category, **overrides):
    """Valid SongForm data"""
    data = {
        "name": "Created Song",
        "capo": 0,
        "author": "",
        "link": "",
        "text": "{C}Hello",
        "categories": [category.pk],
    }
    data.update(overrides)
    return data


def prime_songs_cache(client):
    """Fills the anonymous songs JSON cache so its invalidation becomes observable"""
    client.get(reverse("chords:all_data"))


def songs_cache(tenant):
    return cache.get(tenant_cache_key(tenant, ALL_SONGS_KEY))


def test_create_adds_song(staff_client, category):
    """Posting the add form stores a new song in the category"""
    response = staff_client.post(reverse("backend:add"), song_payload(category))

    assert response.status_code == 302
    song = Song.objects.get(name="Created Song")
    assert list(song.categories.all()) == [category]


def test_create_invalidates_songs_cache(staff_client, anon_client, tenant, category, song):
    """A new song evicts the cached JSON of its categories"""
    prime_songs_cache(anon_client)
    assert songs_cache(tenant) is not None

    staff_client.post(reverse("backend:add"), song_payload(category))

    assert songs_cache(tenant) is None


def test_create_shows_success_message(staff_client, category):
    """The user is told that the song was created"""
    staff_client.post(reverse("backend:add"), song_payload(category))

    assert any("Created Song" in message["text"] for message in pending_messages(staff_client))


def test_create_invalid_form_is_redisplayed(staff_client, category):
    """An empty name redisplays the form instead of saving"""
    response = staff_client.post(reverse("backend:add"), song_payload(category, name=""))

    assert response.status_code == 200
    assert response.context["form"].errors
    assert not Song.objects.filter(name="").exists()


def test_create_only_offers_categories_of_current_tenant(staff_client, category, other_category):
    """The category choices are limited to the tenant being served"""
    response = staff_client.get(reverse("backend:add"))

    choices = response.context["form"].fields["categories"].queryset
    assert category in choices
    assert other_category not in choices


def test_update_changes_song(staff_client, category, song):
    """Posting the edit form stores the new values"""
    url = reverse("backend:edit", kwargs={"pk": song.pk})

    response = staff_client.post(url, song_payload(category, name="Renamed"))

    assert response.status_code == 302
    song.refresh_from_db()
    assert song.name == "Renamed"


def test_update_with_changes_invalidates_songs_cache(staff_client, anon_client, tenant, category, song):
    """A changed song evicts the cached JSON"""
    prime_songs_cache(anon_client)

    staff_client.post(reverse("backend:edit", kwargs={"pk": song.pk}), song_payload(category, name="Renamed"))

    assert songs_cache(tenant) is None


def test_update_without_changes_schedules_no_pdf(staff_client, make_category, make_song, tenant):
    """Resubmitting identical data does not trigger PDF regeneration"""
    category = make_category(tenant, name="Printed", slug="printed", generate_pdf=True)
    song = make_song(category, name="Same", text="{C}same")
    unchanged = song_payload(category, name=song.name, text=song.text, capo=song.capo)

    staff_client.post(reverse("backend:edit", kwargs={"pk": song.pk}), unchanged)

    assert not PDFFile.objects.filter(template=category).exists()


def test_update_page_shows_title(staff_client, song):
    """The edit page is titled after the song being edited"""
    response = staff_client.get(reverse("backend:edit", kwargs={"pk": song.pk}))

    assert song.name in response.context["title"]


def test_delete_page_shows_identifier(staff_client, song):
    """The confirmation page names the song about to be removed"""
    response = staff_client.get(reverse("backend:delete", kwargs={"pk": song.pk}))

    assert response.context["identifier"] == song.name


def test_delete_removes_song(staff_client, song):
    """Confirming the deletion removes the song"""
    response = staff_client.post(reverse("backend:delete", kwargs={"pk": song.pk}))

    assert response.status_code == 302
    assert not Song.objects.filter(pk=song.pk).exists()


def test_delete_invalidates_songs_cache(staff_client, anon_client, tenant, song):
    """Removing a song evicts the cached JSON of its categories"""
    prime_songs_cache(anon_client)

    staff_client.post(reverse("backend:delete", kwargs={"pk": song.pk}))

    assert songs_cache(tenant) is None


def test_delete_shows_success_message(staff_client, song):
    """The user is told that the song was deleted"""
    staff_client.post(reverse("backend:delete", kwargs={"pk": song.pk}))

    assert any("Test Song" in message["text"] for message in pending_messages(staff_client))


def test_saving_schedules_pdf_for_generating_categories(staff_client, make_category, tenant):
    """Categories with PDF generation enabled get a file scheduled on change"""
    category = make_category(tenant, name="Printed", slug="printed", generate_pdf=True)

    staff_client.post(reverse("backend:add"), song_payload(category))

    assert PDFFile.objects.filter(template=category).exists()


def test_saving_does_not_schedule_pdf_twice(staff_client, make_category, tenant, song):
    """A pending file is not duplicated by a second change"""
    category = make_category(tenant, name="Printed", slug="printed", generate_pdf=True)

    staff_client.post(reverse("backend:add"), song_payload(category))
    staff_client.post(reverse("backend:add"), song_payload(category, name="Another"))

    assert PDFFile.objects.filter(template=category).count() == 1
