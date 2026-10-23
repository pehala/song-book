"""Tests for the manual PDF template pages."""

import pytest
from django.urls import reverse

from pdf.models import Status
from pdf.models.request import ManualPDFTemplate, PDFFile, PDFSong

pytestmark = pytest.mark.django_db


def template_payload(**overrides):
    """Valid ManualTemplateForm data, prefixed as the view expects"""
    data = {
        "template-name": "Campfire",
        "template-display_name": "",
        "template-filename": "campfire",
        "template-title": "",
        "template-locale": "en",
        "template-link": "",
        "template-public": "on",
        "template-show_date": "on",
    }
    data.update(overrides)
    return data


def songs_formset_payload(*pairs):
    """Management form plus one entry per (song, number) pair"""
    data = {
        "songs-TOTAL_FORMS": str(len(pairs)),
        "songs-INITIAL_FORMS": "0",
        "songs-MIN_NUM_FORMS": "1",
        "songs-MAX_NUM_FORMS": "1000",
    }
    for index, (song, number) in enumerate(pairs):
        data[f"songs-{index}-song"] = str(song.pk)
        data[f"songs-{index}-song_number"] = str(number)
        data[f"songs-{index}-name"] = song.name
    return data


def test_list_shows_templates_of_this_tenant_only(staff_client, manual_template, other_tenant):
    """The template list is scoped to the tenant being served"""
    foreign = ManualPDFTemplate.objects.create(tenant=other_tenant, name="Foreign", filename="foreign", locale="en")

    listed = staff_client.get(reverse("pdf:templates:list")).context["templates"]

    assert manual_template in listed
    assert foreign not in listed


def test_new_page_offers_the_songs_of_this_tenant(staff_client, song, other_category, make_song):
    """Only songs reachable through this tenant can be selected"""
    foreign = make_song(other_category, name="Foreign Song")

    offered = staff_client.get(reverse("pdf:templates:new")).context["songs"]

    assert song in offered
    assert foreign not in offered


def test_new_page_lists_the_categories(staff_client, category):
    """The category filter is filled with this tenant's categories"""
    response = staff_client.get(reverse("pdf:templates:new"))

    assert category in response.context["categories"]
    assert category.slug in response.context["slugs"]


def test_edit_page_preselects_the_stored_songs(staff_client, manual_template, pdf_song_entry, pdf_song):
    """Reopening a template shows the songs it already holds"""
    response = staff_client.get(reverse("pdf:templates:edit", kwargs={"pk": manual_template.pk}))

    assert response.context["initial_songs"] == [pdf_song.pk]
    assert response.context["template_form"].instance == manual_template


def test_creating_a_template_stores_it(staff_client, song):
    """Submitting the first step creates the template"""
    response = staff_client.post(
        reverse("pdf:templates:new"),
        template_payload() | {"songs": [str(song.pk)]},
    )

    assert response.status_code == 200
    assert ManualPDFTemplate.objects.filter(name="Campfire").exists()


def test_creating_a_template_asks_for_song_numbers(staff_client, song):
    """The first step hands over to the numbering page"""
    response = staff_client.post(
        reverse("pdf:templates:new"),
        template_payload() | {"songs": [str(song.pk)]},
    )

    assert "pdf/templates/assign.html" in [template.name for template in response.templates]
    assert response.context["formset"].initial == [{"name": song.name, "song_number": 1, "song": song}]


def test_updating_a_template_keeps_its_identity(staff_client, manual_template, song):
    """Editing an existing template does not create a second one"""
    staff_client.post(
        reverse("pdf:templates:edit", kwargs={"pk": manual_template.pk}),
        template_payload(**{"template-name": "Renamed"}) | {"songs": [str(song.pk)]},
    )

    manual_template.refresh_from_db()
    assert manual_template.name == "Renamed"
    assert ManualPDFTemplate.objects.count() == 1


def test_template_without_songs_is_rejected(staff_client, song):
    """A template has to print at least one song"""
    response = staff_client.post(reverse("pdf:templates:new"), template_payload())

    assert response.status_code == 200
    assert response.context["songs_form"].errors
    assert not ManualPDFTemplate.objects.filter(name="Campfire").exists()


def test_invalid_template_form_is_redisplayed(staff_client, song):
    """A template without a name comes back as a form"""
    response = staff_client.post(
        reverse("pdf:templates:new"),
        template_payload(**{"template-name": ""}) | {"songs": [str(song.pk)]},
    )

    assert response.context["template_form"].errors


def test_assigning_numbers_stores_the_songs(staff_client, manual_template, song, make_song, category):
    """The second step replaces the songs of the template"""
    second = make_song(category, name="Second Song")

    response = staff_client.post(
        reverse("pdf:templates:assign", kwargs={"pk": manual_template.pk}),
        songs_formset_payload((song, 1), (second, 2)),
    )

    assert response.status_code == 302
    assert manual_template.get_songs() == [(1, song), (2, second)]


def test_duplicate_song_numbers_are_rejected(staff_client, manual_template, pdf_song_entry, make_song, pdf_category):
    """Two songs cannot share a position in the booklet"""
    second = make_song(pdf_category, name="Second Song")

    response = staff_client.post(
        reverse("pdf:templates:assign", kwargs={"pk": manual_template.pk}),
        songs_formset_payload((pdf_song_entry.song, 1), (second, 1)),
    )

    assert response.status_code == 200
    assert "pdf/templates/assign.html" in [template.name for template in response.templates]
    assert response.context["formset"].non_form_errors()
    assert manual_template.get_songs() == [(1, pdf_song_entry.song)]


def test_opening_the_numbering_page_directly_redirects(staff_client, manual_template):
    """The second step is not reachable on its own"""
    response = staff_client.get(reverse("pdf:templates:assign", kwargs={"pk": manual_template.pk}))

    assert response.status_code == 302
    assert response["Location"] == reverse("pdf:templates:edit", kwargs={"pk": manual_template.pk})


def test_generating_schedules_a_file(staff_client, manual_template, pdf_song_entry, mock_weasyprint):
    """The generate link creates a file and sends the user to its waiting page"""
    response = staff_client.get(reverse("pdf:templates:generate", kwargs={"pk": manual_template.pk}))

    file = PDFFile.objects.get(template=manual_template)
    assert response.status_code == 302
    assert response["Location"] == reverse("pdf:files:wait", kwargs={"pk": file.pk})


def test_generating_twice_is_refused(staff_client, manual_template, make_pdf_file):
    """A template already waiting for a file does not queue a second one"""
    make_pdf_file(manual_template, status=Status.SCHEDULED)

    response = staff_client.get(reverse("pdf:templates:generate", kwargs={"pk": manual_template.pk}))

    assert response["Location"] == reverse("pdf:templates:list")
    assert PDFFile.objects.filter(template=manual_template).count() == 1


def test_deleting_removes_the_template(staff_client, manual_template):
    """Confirming the deletion removes the template and its songs"""
    response = staff_client.post(reverse("pdf:templates:delete", kwargs={"pk": manual_template.pk}))

    assert response.status_code == 302
    assert not ManualPDFTemplate.objects.filter(pk=manual_template.pk).exists()
    assert not PDFSong.objects.filter(request_id=manual_template.pk).exists()


def test_move_reassigns_the_template(superuser_client, manual_template, other_tenant):
    """Templates can be handed over to another tenant"""
    response = superuser_client.post(
        reverse("pdf:templates:move"),
        {
            "tenant": other_tenant.pk,
            "form-TOTAL_FORMS": "1",
            "form-INITIAL_FORMS": "1",
            "form-MIN_NUM_FORMS": "0",
            "form-MAX_NUM_FORMS": "1000",
            "form-0-pk": str(manual_template.pk),
            "form-0-name": manual_template.name,
        },
    )

    assert response.status_code == 302
    manual_template.refresh_from_db()
    assert manual_template.tenant == other_tenant
