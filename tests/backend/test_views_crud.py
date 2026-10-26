"""Tests for creating, updating and deleting songs."""

import json

import pytest
from django.urls import reverse

from backend.models import Song
from pdf.models import Status
from pdf.models.request import AllSongsTemplate, PDFFile

pytestmark = pytest.mark.django_db


def pending_messages(client):
    """The messages the reader receives from /api/me after the redirect."""
    return json.loads(client.get(reverse("chords:me")).content)["messages"]


def song_payload(category, **overrides):
    """Valid SongForm data."""
    data = {
        "name": "Created Song",
        "capo": 0,
        "pdf_columns": 2,
        "author": "",
        "link": "",
        "text": "{C}Hello",
        "categories": [category.pk],
    }
    data.update(overrides)
    return data


def test_create_adds_song(staff_client, category):
    """Posting the add form stores a new song in the category."""
    response = staff_client.post(reverse("backend:add"), song_payload(category))

    assert response.status_code == 302
    song = Song.objects.get(name="Created Song")
    assert list(song.categories.all()) == [category]


def test_create_shows_success_message(staff_client, category):
    """The user is told that the song was created."""
    staff_client.post(reverse("backend:add"), song_payload(category))

    assert any("Created Song" in message["text"] for message in pending_messages(staff_client))


def test_create_invalid_form_is_redisplayed(staff_client, category):
    """An empty name redisplays the form instead of saving."""
    response = staff_client.post(reverse("backend:add"), song_payload(category, name=""))

    assert response.status_code == 200
    assert response.context["form"].errors
    assert not Song.objects.filter(name="").exists()


def test_create_only_offers_categories_of_current_tenant(staff_client, category, other_category):
    """The category choices are limited to the tenant being served."""
    response = staff_client.get(reverse("backend:add"))

    choices = response.context["form"].fields["categories"].queryset
    assert category in choices
    assert other_category not in choices


def test_update_changes_song(staff_client, category, song):
    """Posting the edit form stores the new values."""
    url = reverse("backend:edit", kwargs={"pk": song.pk})

    response = staff_client.post(url, song_payload(category, name="Renamed"))

    assert response.status_code == 302
    song.refresh_from_db()
    assert song.name == "Renamed"


def test_update_without_changes_schedules_no_pdf(staff_client, make_category, make_song, tenant):
    """Resubmitting identical data does not trigger PDF regeneration."""
    category = make_category(tenant, name="Printed", slug="printed", generate_pdf=True)
    song = make_song(category, name="Same", text="{C}same")
    unchanged = song_payload(category, name=song.name, text=song.text, capo=song.capo)

    staff_client.post(reverse("backend:edit", kwargs={"pk": song.pk}), unchanged)

    assert not PDFFile.objects.filter(template=category).exists()


def test_update_page_shows_title(staff_client, song):
    """The edit page is titled after the song being edited."""
    response = staff_client.get(reverse("backend:edit", kwargs={"pk": song.pk}))

    assert song.name in response.context["title"]


def test_delete_page_shows_identifier(staff_client, song):
    """The confirmation page names the song about to be removed."""
    response = staff_client.get(reverse("backend:delete", kwargs={"pk": song.pk}))

    assert response.context["identifier"] == song.name


def test_delete_removes_song(staff_client, song):
    """Confirming the deletion removes the song."""
    response = staff_client.post(reverse("backend:delete", kwargs={"pk": song.pk}))

    assert response.status_code == 302
    assert not Song.objects.filter(pk=song.pk).exists()


def test_delete_shows_success_message(staff_client, song):
    """The user is told that the song was deleted."""
    staff_client.post(reverse("backend:delete", kwargs={"pk": song.pk}))

    assert any("Test Song" in message["text"] for message in pending_messages(staff_client))


def test_saving_schedules_pdf_for_generating_categories(staff_client, make_category, tenant):
    """Categories with PDF generation enabled get a file scheduled on change."""
    category = make_category(tenant, name="Printed", slug="printed", generate_pdf=True)

    staff_client.post(reverse("backend:add"), song_payload(category))

    assert PDFFile.objects.filter(template=category).exists()


def test_saving_does_not_schedule_pdf_twice(staff_client, make_category, tenant, song):
    """A pending file is not duplicated by a second change."""
    category = make_category(tenant, name="Printed", slug="printed", generate_pdf=True)

    staff_client.post(reverse("backend:add"), song_payload(category))
    staff_client.post(reverse("backend:add"), song_payload(category, name="Another"))

    assert PDFFile.objects.filter(template=category).count() == 1


def test_saving_schedules_the_all_songs_pdf(staff_client, category, all_songs_template):
    """A song change also schedules the PDF with every song of the tenant."""
    staff_client.post(reverse("backend:add"), song_payload(category))

    assert PDFFile.objects.filter(template=all_songs_template).count() == 1


def test_saving_schedules_the_all_songs_pdf_once_for_many_categories(
    staff_client, tenant, category, make_category, all_songs_template
):
    """A song in two categories of one tenant schedules a single all songs file."""
    second = make_category(tenant, name="Second", slug="second")

    staff_client.post(reverse("backend:add"), song_payload(category, categories=[category.pk, second.pk]))

    assert PDFFile.objects.filter(template=all_songs_template).count() == 1


def test_saving_skips_the_all_songs_pdf_when_disabled(staff_client, category, all_songs_template):
    """The all songs PDF is only generated when the template asks for it."""
    all_songs_template.generate_pdf = False
    all_songs_template.save()

    staff_client.post(reverse("backend:add"), song_payload(category))

    assert not PDFFile.objects.filter(template=all_songs_template).exists()


def test_saving_skips_the_all_songs_pdf_without_the_list(staff_client, tenant, category, all_songs_template):
    """A tenant without the all songs list gets no all songs PDF."""
    tenant.all_songs_category = False
    tenant.save()

    staff_client.post(reverse("backend:add"), song_payload(category))

    assert not PDFFile.objects.filter(template=all_songs_template).exists()


def test_saving_without_an_all_songs_template_schedules_nothing(staff_client, category):
    """The template is created by whoever opens the category list, not by a song change."""
    staff_client.post(reverse("backend:add"), song_payload(category))

    assert not AllSongsTemplate.objects.exists()


def test_deleting_a_song_schedules_the_all_songs_pdf(staff_client, song, all_songs_template):
    """A removed song changes the all songs PDF as well."""
    staff_client.post(reverse("backend:delete", kwargs={"pk": song.pk}))

    assert PDFFile.objects.filter(template=all_songs_template).exists()


@pytest.fixture
def printed_category(tenant, make_category):
    """A category whose PDF is generated automatically."""
    return make_category(tenant, name="Printed", slug="printed", generate_pdf=True)


@pytest.fixture(params=["printed_category", "all_songs_template"])
def printed(request, printed_category, all_songs_template):
    """Each template an edit of a song in `printed_category` schedules a PDF for."""
    return request.getfixturevalue(request.param)


def test_several_edits_schedule_one_file(staff_client, printed_category, printed):
    """Edits landing while a file is pending do not queue more of them."""
    staff_client.post(reverse("backend:add"), song_payload(printed_category, name="First"))
    staff_client.post(reverse("backend:add"), song_payload(printed_category, name="Second"))
    first = Song.objects.get(name="First")
    staff_client.post(reverse("backend:edit", kwargs={"pk": first.pk}), song_payload(printed_category, name="Renamed"))

    assert PDFFile.objects.filter(template=printed).count() == 1


@pytest.mark.parametrize("status", [Status.DONE, Status.FAILED])
def test_an_edit_after_the_file_finished_schedules_another(staff_client, printed_category, printed, status):
    """Once the pending file is finished, the next edit queues a fresh one."""
    staff_client.post(reverse("backend:add"), song_payload(printed_category, name="First"))
    PDFFile.objects.filter(template=printed).update(status=status)

    staff_client.post(reverse("backend:add"), song_payload(printed_category, name="Second"))

    assert list(PDFFile.objects.filter(template=printed).order_by("pk").values_list("status", flat=True)) == [
        status,
        Status.SCHEDULED,
    ]


def test_an_edit_and_a_delete_schedule_one_file(staff_client, printed_category, printed):
    """Removing a song that was just added joins the file already pending."""
    staff_client.post(reverse("backend:add"), song_payload(printed_category, name="First"))
    staff_client.post(reverse("backend:delete", kwargs={"pk": Song.objects.get(name="First").pk}))

    assert PDFFile.objects.filter(template=printed).count() == 1


@pytest.mark.parametrize("name", ["backend:edit", "backend:delete"])
def test_pages_of_a_song_of_another_tenant_are_not_found(staff_client, other_category, make_song, name):
    """A local admin cannot reach songs listed only by another tenant."""
    foreign = make_song(other_category, name="Foreign Song")

    response = staff_client.get(reverse(name, kwargs={"pk": foreign.pk}))

    assert response.status_code == 404


def test_song_of_another_tenant_cannot_be_updated(staff_client, category, other_category, make_song):
    """Saving the edit form of a foreign song changes nothing."""
    foreign = make_song(other_category, name="Foreign Song")

    response = staff_client.post(reverse("backend:edit", kwargs={"pk": foreign.pk}), song_payload(category))

    assert response.status_code == 404
    foreign.refresh_from_db()
    assert foreign.name == "Foreign Song"
    assert list(foreign.categories.all()) == [other_category]


def test_song_of_another_tenant_cannot_be_deleted(staff_client, other_category, make_song):
    """Confirming the deletion of a foreign song leaves it in place."""
    foreign = make_song(other_category, name="Foreign Song")

    response = staff_client.post(reverse("backend:delete", kwargs={"pk": foreign.pk}))

    assert response.status_code == 404
    assert Song.objects.filter(pk=foreign.pk).exists()


def test_update_keeps_the_categories_of_other_tenants(staff_client, category, other_category, make_song):
    """A song shared with another tenant stays in that tenant's categories."""
    shared = make_song(category, other_category, name="Shared Song")

    staff_client.post(reverse("backend:edit", kwargs={"pk": shared.pk}), song_payload(category, name="Renamed"))

    shared.refresh_from_db()
    assert shared.name == "Renamed"
    assert set(shared.categories.all()) == {category, other_category}


def test_delete_of_a_shared_song_only_leaves_this_tenant(staff_client, category, other_category, make_song):
    """A song another tenant lists as well is taken out of this tenant's categories instead of being deleted."""
    shared = make_song(category, other_category, name="Shared Song")

    response = staff_client.post(reverse("backend:delete", kwargs={"pk": shared.pk}))

    assert response.status_code == 302
    assert list(shared.categories.all()) == [other_category]
