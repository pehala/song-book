"""Tests for the all songs row of the category list and the form behind it."""

import pytest
from django.urls import reverse

from pdf.models.request import AllSongsTemplate, PDFFile

pytestmark = pytest.mark.django_db

EDIT_URL = reverse("category:edit_all")


def all_songs_payload(**overrides):
    """Valid AllSongsForm data."""
    data = {
        "filename": "everything",
        "locale": "en",
        "title": "",
        "display_name": "",
        "link": "",
        "generate_pdf": False,
        "category_sections": False,
        "public": True,
        "show_date": True,
    }
    data.update(overrides)
    return data


def test_list_creates_the_template_with_defaults(staff_client, tenant):
    """The first visit creates the tenant's template, named and titled after the tenant."""
    listed = staff_client.get(reverse("category:list")).context["all_songs"]

    assert listed == AllSongsTemplate.objects.get(tenant=tenant)
    assert listed.filename == "all-songs"
    assert listed.title == tenant.display_name
    assert not listed.generate_pdf


def test_list_reuses_the_template(staff_client, all_songs_template):
    """Later visits show the stored template."""
    listed = staff_client.get(reverse("category:list")).context["all_songs"]

    assert listed == all_songs_template
    assert AllSongsTemplate.objects.count() == 1


def test_list_counts_active_songs_and_files(staff_client, song, archived_song, all_songs_template, make_category):
    """The row counts the songs of every category once, archived ones excluded, and the files made so far."""
    song.categories.add(make_category(all_songs_template.tenant, name="Second", slug="second"))
    PDFFile.objects.create(tenant=all_songs_template.tenant, template=all_songs_template, filename="all")

    listed = staff_client.get(reverse("category:list")).context["all_songs"]

    assert (listed.song_count, listed.file_count) == (1, 1)


def test_list_shows_the_row_for_the_tenant_only(staff_client, other_tenant, tenant):
    """Other tenants' templates are not listed."""
    other = AllSongsTemplate.for_tenant(other_tenant, filename="other", locale="en")

    assert staff_client.get(reverse("category:list")).context["all_songs"] != other


def test_list_links_the_row_to_the_all_songs_list_and_form(staff_client, all_songs_template):
    """The row leads to /all and to the form."""
    content = staff_client.get(reverse("category:list")).content.decode()

    assert f'href="{reverse("backend:all")}"' in content
    assert f'href="{EDIT_URL}"' in content


def test_list_hints_when_the_list_is_hidden(staff_client, tenant, all_songs_template):
    """A tenant without the all songs list is told where to turn it on."""
    tenant.all_songs_category = False
    tenant.save()

    content = staff_client.get(reverse("category:list")).content.decode()

    assert f'href="{reverse("tenants:edit")}"' in content
    assert 'class="table-secondary"' in content


def test_list_has_no_hint_when_the_list_is_shown(staff_client, all_songs_template):
    """The hint only appears for a hidden list."""
    content = staff_client.get(reverse("category:list")).content.decode()

    assert f'href="{reverse("tenants:edit")}"' not in content
    assert "table-secondary" not in content


def test_form_shows_the_template_of_the_tenant(staff_client, all_songs_template):
    """The edit page works on the template of the tenant being served."""
    response = staff_client.get(EDIT_URL)

    assert response.context["object"] == all_songs_template
    assert set(response.context["form"].fields) == set(all_songs_payload()) | {"image", "name"}


def test_form_starts_with_the_read_only_name(staff_client, all_songs_template):
    """The name of the list is shown, but cannot be changed."""
    form = staff_client.get(EDIT_URL).context["form"]

    assert next(iter(form.fields)) == "name"
    assert form["name"].value() == "Všechny Písničky"
    assert form.fields["name"].disabled


def test_update_ignores_a_posted_name(staff_client, all_songs_template):
    """The name is not stored, wherever it comes from."""
    staff_client.post(EDIT_URL, all_songs_payload(name="Hacked"))

    assert staff_client.get(EDIT_URL).context["form"]["name"].value() == "Všechny Písničky"


def test_form_is_titled_after_the_pdf(staff_client, all_songs_template):
    """The page title names the all songs PDF."""
    assert staff_client.get(EDIT_URL).context["title"] == "Upravit PDF všech písniček"


def test_update_stores_the_values(staff_client, all_songs_template):
    """Posting the form changes the template."""
    response = staff_client.post(EDIT_URL, all_songs_payload(filename="renamed"))

    assert response.status_code == 302
    all_songs_template.refresh_from_db()
    assert all_songs_template.filename == "renamed"


def test_update_stores_the_sections_choice(staff_client, all_songs_template):
    """The sections by category are switched on and off with the form."""
    staff_client.post(EDIT_URL, all_songs_payload(category_sections=True))
    all_songs_template.refresh_from_db()
    assert all_songs_template.category_sections

    staff_client.post(EDIT_URL, all_songs_payload())
    all_songs_template.refresh_from_db()
    assert not all_songs_template.category_sections


def test_update_schedules_pdf_when_enabled(staff_client, all_songs_template):
    """Changing a printed template queues a fresh PDF."""
    staff_client.post(EDIT_URL, all_songs_payload(generate_pdf=True))

    assert PDFFile.objects.filter(template=all_songs_template).count() == 1


def test_update_without_changes_schedules_nothing(staff_client, tenant):
    """Resubmitting identical data does not queue a PDF."""
    template = AllSongsTemplate.for_tenant(
        tenant, filename="everything", locale="en", generate_pdf=True, title="", display_name="", link=""
    )

    staff_client.post(EDIT_URL, all_songs_payload(generate_pdf=True))

    assert not PDFFile.objects.filter(template=template).exists()


def test_update_schedules_nothing_when_disabled(staff_client, all_songs_template):
    """Without automatic generation saving only stores the values."""
    all_songs_template.generate_pdf = False
    all_songs_template.save()

    staff_client.post(EDIT_URL, all_songs_payload(title="New"))

    assert not PDFFile.objects.filter(template=all_songs_template).exists()


def test_update_schedules_nothing_without_the_list(staff_client, tenant, all_songs_template):
    """A tenant without the all songs list gets no all songs PDF."""
    tenant.all_songs_category = False
    tenant.save()

    staff_client.post(EDIT_URL, all_songs_payload(generate_pdf=True))

    assert not PDFFile.objects.filter(template=all_songs_template).exists()


def test_invalid_update_schedules_nothing(staff_client, all_songs_template):
    """A rejected form changes nothing."""
    response = staff_client.post(EDIT_URL, all_songs_payload(generate_pdf=True, filename=""))

    assert response.status_code == 200
    assert not PDFFile.objects.filter(template=all_songs_template).exists()
