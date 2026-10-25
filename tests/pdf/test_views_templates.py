"""Tests for the manual PDF template pages."""

import pytest
from django.conf import settings
from django.core.cache import cache
from django.urls import reverse

from pdf.models import Section, Status
from pdf.models.request import AllSongsTemplate, ManualPDFTemplate, PDFFile, PDFSong
from tenants.utils import tenant_cache_key

pytestmark = pytest.mark.django_db


def template_payload(**overrides):
    """Valid ManualTemplateForm data, prefixed as the view expects."""
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
    """Management form plus one entry per (song, number) pair, or (song, number, section) triple."""
    data = {
        "songs-TOTAL_FORMS": str(len(pairs)),
        "songs-INITIAL_FORMS": "0",
        "songs-MIN_NUM_FORMS": "1",
        "songs-MAX_NUM_FORMS": "1000",
    }
    for index, (song, number, *section) in enumerate(pairs):
        data[f"songs-{index}-song"] = str(song.pk)
        data[f"songs-{index}-song_number"] = str(number)
        data[f"songs-{index}-section"] = "".join(section)
        data[f"songs-{index}-name"] = song.name
    return data


def test_list_shows_templates_of_this_tenant_only(staff_client, manual_template, other_tenant):
    """The template list is scoped to the tenant being served."""
    foreign = ManualPDFTemplate.objects.create(tenant=other_tenant, name="Foreign", filename="foreign", locale="en")

    listed = staff_client.get(reverse("pdf:templates:list")).context["templates"]

    assert manual_template in listed
    assert foreign not in listed


def test_new_page_offers_the_songs_of_this_tenant(staff_client, song, other_category, make_song):
    """Only songs reachable through this tenant can be selected."""
    foreign = make_song(other_category, name="Foreign Song")

    offered = staff_client.get(reverse("pdf:templates:new")).context["songs"]

    assert song in offered
    assert foreign not in offered


def test_new_page_translates_the_song_table_headers(staff_client):
    """The headers of the table of selectable songs are in the language of the page."""
    html = staff_client.get(reverse("pdf:templates:new")).content.decode()

    assert "<th>Autor</th>" in html
    assert '<th class="d-none">Kategorie</th>' in html


def test_new_page_offers_the_choice_of_sections(staff_client, song):
    """The song selection shows the choice of sections as a form field, not as escaped markup."""
    content = staff_client.get(reverse("pdf:templates:new")).content.decode()

    assert '<select name="sections"' in content
    assert "&lt;select" not in content


def test_new_page_lists_the_categories(staff_client, category):
    """The category filter is filled with this tenant's categories."""
    response = staff_client.get(reverse("pdf:templates:new"))

    assert category in response.context["categories"]
    assert category.slug in response.context["slugs"]


def test_edit_page_preselects_the_stored_songs(staff_client, manual_template, pdf_song_entry, pdf_song):
    """Reopening a template shows the songs it already holds."""
    response = staff_client.get(reverse("pdf:templates:edit", kwargs={"pk": manual_template.pk}))

    assert response.context["initial_songs"] == [pdf_song.pk]
    assert response.context["template_form"].instance == manual_template


def test_creating_a_template_stores_it(staff_client, song):
    """Submitting the first step creates the template."""
    response = staff_client.post(
        reverse("pdf:templates:new"),
        template_payload() | {"songs": [str(song.pk)]},
    )

    assert response.status_code == 200
    assert ManualPDFTemplate.objects.filter(name="Campfire").exists()


def test_creating_a_template_asks_for_song_numbers(staff_client, song):
    """The first step hands over to the numbering page."""
    response = staff_client.post(
        reverse("pdf:templates:new"),
        template_payload() | {"songs": [str(song.pk)]},
    )

    assert "pdf/templates/assign.html" in [template.name for template in response.templates]
    assert response.context["formset"].initial == [{"name": song.name, "song_number": 1, "song": song, "section": ""}]


def test_the_songs_can_start_in_a_section_for_each_category(staff_client, tenant, category, make_category, make_song):
    """Asking for sections by category prefills the numbering page with the songs under their categories."""
    second_category = make_category(tenant, name="Second", slug="second")
    first = make_song(category, name="First")
    second = make_song(second_category, name="Second")

    response = staff_client.post(
        reverse("pdf:templates:new"),
        template_payload() | {"songs": [str(second.pk), str(first.pk)], "sections": "category"},
    )

    assert [(row["song_number"], row["song"], row["section"]) for row in response.context["formset"].initial] == [
        (1, first, category.name),
        (2, second, "Second"),
    ]


def test_sections_by_category_use_the_own_categories(staff_client, category, other_category, make_song):
    """A song that is also in a category of another tenant is sectioned by this tenant's category, and none is lost."""
    shared = make_song(category, other_category, name="Shared")
    mine = make_song(category, name="Mine")

    response = staff_client.post(
        reverse("pdf:templates:new"),
        template_payload() | {"songs": [str(mine.pk), str(shared.pk)], "sections": "category"},
    )

    assert [(row["song"], row["section"]) for row in response.context["formset"].initial] == [
        (shared, category.name),
        (mine, category.name),
    ]


def test_editing_a_template_starts_from_its_order_and_sections(
    staff_client, manual_template, pdf_song, pdf_category, make_song
):
    """The songs the template has keep their order and section, and the song added follows them without one."""
    first = make_song(pdf_category, name="First")
    added = make_song(pdf_category, name="Added")
    PDFSong.objects.create(song=pdf_song, request=manual_template, song_number=1, section="Camp")
    PDFSong.objects.create(song=first, request=manual_template, song_number=2, section="Camp")

    response = staff_client.post(
        reverse("pdf:templates:edit", kwargs={"pk": manual_template.pk}),
        template_payload() | {"songs": [str(song.pk) for song in (added, first, pdf_song)]},
    )

    assert [(row["song_number"], row["song"], row["section"]) for row in response.context["formset"].initial] == [
        (1, pdf_song, "Camp"),
        (2, first, "Camp"),
        (3, added, ""),
    ]


def test_the_numbering_page_has_a_heading_where_the_section_changes(
    staff_client, manual_template, pdf_song, pdf_category, make_song
):
    """A heading row, with its title in it, comes before the first song of each section, plus the one to copy."""
    others = [make_song(pdf_category, name=name) for name in ("Second", "Third")]
    PDFSong.objects.create(song=pdf_song, request=manual_template, song_number=1)
    PDFSong.objects.create(song=others[0], request=manual_template, song_number=2, section="Camp")
    PDFSong.objects.create(song=others[1], request=manual_template, song_number=3, section="")

    response = staff_client.post(
        reverse("pdf:templates:edit", kwargs={"pk": manual_template.pk}),
        template_payload() | {"songs": [str(song.pk) for song in (pdf_song, *others)]},
    )

    content = response.content.decode()
    rows = content.split('<template id="section-template">')[0]
    assert rows.count('class="section-row') == 2
    assert 'value="Camp"' in rows
    assert 'value=""' in rows
    assert rows.index('value="Camp"') < rows.index('value=""')
    assert content.count('class="section-row') == 3


def test_a_song_before_any_heading_has_none(staff_client, manual_template, pdf_song, make_song, pdf_category):
    """Songs without a section at the start of the list need no heading."""
    PDFSong.objects.create(song=pdf_song, request=manual_template, song_number=1)

    response = staff_client.post(
        reverse("pdf:templates:edit", kwargs={"pk": manual_template.pk}),
        template_payload() | {"songs": [str(pdf_song.pk)]},
    )

    assert response.content.decode().split('<template id="section-template">')[0].count('class="section-row') == 0


def test_updating_a_template_keeps_its_identity(staff_client, manual_template, song):
    """Editing an existing template does not create a second one."""
    staff_client.post(
        reverse("pdf:templates:edit", kwargs={"pk": manual_template.pk}),
        template_payload(**{"template-name": "Renamed"}) | {"songs": [str(song.pk)]},
    )

    manual_template.refresh_from_db()
    assert manual_template.name == "Renamed"
    assert ManualPDFTemplate.objects.count() == 1


def test_template_without_songs_is_rejected(staff_client, song):
    """A template has to print at least one song."""
    response = staff_client.post(reverse("pdf:templates:new"), template_payload())

    assert response.status_code == 200
    assert response.context["songs_form"].errors
    assert not ManualPDFTemplate.objects.filter(name="Campfire").exists()


def test_invalid_template_form_is_redisplayed(staff_client, song):
    """A template without a name comes back as a form."""
    response = staff_client.post(
        reverse("pdf:templates:new"),
        template_payload(**{"template-name": ""}) | {"songs": [str(song.pk)]},
    )

    assert response.context["template_form"].errors


def test_assigning_numbers_stores_the_songs(staff_client, manual_template, song, make_song, category):
    """The second step replaces the songs of the template."""
    second = make_song(category, name="Second Song")

    response = staff_client.post(
        reverse("pdf:templates:assign", kwargs={"pk": manual_template.pk}),
        songs_formset_payload((song, 1), (second, 2)),
    )

    assert response.status_code == 302
    assert manual_template.get_songs() == [(1, song), (2, second)]


def test_assigning_numbers_stores_the_sections(staff_client, manual_template, song, make_song, category):
    """The section of every row is stored with the song and divides the template."""
    second = make_song(category, name="Second Song")
    third = make_song(category, name="Third Song")

    staff_client.post(
        reverse("pdf:templates:assign", kwargs={"pk": manual_template.pk}),
        songs_formset_payload((song, 1), (second, 2, "Camp"), (third, 3, "Camp")),
    )

    assert manual_template.get_sections() == [
        Section(None, [(1, song)]),
        Section("Camp", [(2, second), (3, third)]),
    ]


def test_a_section_that_comes_back_is_rejected(staff_client, manual_template, song, make_song, category):
    """The page is shown again with the error and nothing is stored."""
    second = make_song(category, name="Second Song")
    third = make_song(category, name="Third Song")

    response = staff_client.post(
        reverse("pdf:templates:assign", kwargs={"pk": manual_template.pk}),
        songs_formset_payload((song, 1, "Camp"), (second, 2, "Evening"), (third, 3, "Camp")),
    )

    assert response.status_code == 200
    assert response.context["formset"].non_form_errors()
    assert manual_template.get_songs() == []


def test_duplicate_song_numbers_are_rejected(staff_client, manual_template, pdf_song_entry, make_song, pdf_category):
    """Two songs cannot share a position in the booklet."""
    second = make_song(pdf_category, name="Second Song")

    response = staff_client.post(
        reverse("pdf:templates:assign", kwargs={"pk": manual_template.pk}),
        songs_formset_payload((pdf_song_entry.song, 1), (second, 1)),
    )

    assert response.status_code == 200
    assert "pdf/templates/assign.html" in [template.name for template in response.templates]
    assert response.context["formset"].non_form_errors()
    assert manual_template.get_songs() == [(1, pdf_song_entry.song)]


def test_assigning_numbers_to_a_template_of_another_tenant_is_refused(staff_client, song, other_tenant):
    """The numbering step only reaches templates of the tenant being served."""
    foreign = ManualPDFTemplate.objects.create(tenant=other_tenant, name="Foreign", filename="foreign", locale="en")

    response = staff_client.post(
        reverse("pdf:templates:assign", kwargs={"pk": foreign.pk}),
        songs_formset_payload((song, 1)),
    )

    assert response.status_code == 404
    assert not PDFSong.objects.filter(request=foreign).exists()


def test_assigning_a_song_of_another_tenant_is_refused(staff_client, manual_template, song, other_category, make_song):
    """Only songs of this tenant can be numbered into its template."""
    foreign = make_song(other_category, name="Foreign Song")

    response = staff_client.post(
        reverse("pdf:templates:assign", kwargs={"pk": manual_template.pk}),
        songs_formset_payload((song, 1), (foreign, 2)),
    )

    assert response.status_code == 200
    assert response.context["formset"].errors[1]
    assert manual_template.get_songs() == []


def test_editing_a_template_of_another_tenant_is_refused(staff_client, song, other_tenant):
    """Neither opening nor saving reaches a template of another tenant."""
    foreign = ManualPDFTemplate.objects.create(tenant=other_tenant, name="Foreign", filename="foreign", locale="en")
    url = reverse("pdf:templates:edit", kwargs={"pk": foreign.pk})

    assert staff_client.get(url).status_code == 404
    response = staff_client.post(url, template_payload(**{"template-name": "Stolen"}) | {"songs": [str(song.pk)]})

    assert response.status_code == 404
    foreign.refresh_from_db()
    assert foreign.name == "Foreign"
    assert foreign.tenant == other_tenant


def test_opening_the_numbering_page_directly_redirects(staff_client, manual_template):
    """The second step is not reachable on its own."""
    response = staff_client.get(reverse("pdf:templates:assign", kwargs={"pk": manual_template.pk}))

    assert response.status_code == 302
    assert response["Location"] == reverse("pdf:templates:edit", kwargs={"pk": manual_template.pk})


def test_generating_schedules_a_file(staff_client, manual_template, pdf_song_entry, mock_weasyprint):
    """The generate link creates a file and sends the user to its waiting page."""
    response = staff_client.get(reverse("pdf:templates:generate", kwargs={"pk": manual_template.pk}))

    file = PDFFile.objects.get(template=manual_template)
    assert response.status_code == 302
    assert response["Location"] == reverse("pdf:files:wait", kwargs={"pk": file.pk})


def test_generating_twice_is_refused(staff_client, manual_template, make_pdf_file):
    """A template already waiting for a file does not queue a second one."""
    make_pdf_file(manual_template, status=Status.SCHEDULED)

    response = staff_client.get(reverse("pdf:templates:generate", kwargs={"pk": manual_template.pk}))

    assert response["Location"] == reverse("pdf:templates:list")
    assert PDFFile.objects.filter(template=manual_template).count() == 1


def test_deleting_removes_the_template(staff_client, manual_template):
    """Confirming the deletion removes the template and its songs."""
    response = staff_client.post(reverse("pdf:templates:delete", kwargs={"pk": manual_template.pk}))

    assert response.status_code == 302
    assert not ManualPDFTemplate.objects.filter(pk=manual_template.pk).exists()
    assert not PDFSong.objects.filter(request_id=manual_template.pk).exists()


def move_payload(target, template):
    """Form plus formset data for the move page."""
    return {
        "tenant": target.pk,
        "form-TOTAL_FORMS": "1",
        "form-INITIAL_FORMS": "1",
        "form-MIN_NUM_FORMS": "0",
        "form-MAX_NUM_FORMS": "1000",
        "form-0-pk": str(template.pk),
        "form-0-name": template.name,
    }


def test_move_reassigns_the_template(superuser_client, manual_template, other_tenant):
    """Templates can be handed over to another tenant."""
    response = superuser_client.post(reverse("pdf:templates:move"), move_payload(other_tenant, manual_template))

    assert response.status_code == 302
    manual_template.refresh_from_db()
    assert manual_template.tenant == other_tenant


def test_generate_from_the_all_songs_template(staff_client, song, all_songs_template, mock_weasyprint):
    """The generate action of the row builds the file from every song of the tenant."""
    response = staff_client.get(reverse("pdf:templates:generate", kwargs={"pk": all_songs_template.pk}))

    assert response.status_code == 302
    assert PDFFile.objects.get(template=all_songs_template).status == "DO"


def test_move_takes_the_generated_files_along(superuser_client, manual_template, make_pdf_file, other_tenant):
    """Files printed from the template follow it to the new tenant."""
    file = make_pdf_file(manual_template, status=Status.DONE)

    superuser_client.post(reverse("pdf:templates:move"), move_payload(other_tenant, manual_template))

    file.refresh_from_db()
    assert file.tenant == other_tenant


def test_move_drops_the_files_menu_of_both_tenants(superuser_client, manual_template, tenant, other_tenant):
    """The file leaves the menu of one tenant and enters the menu of the other."""
    for each in (tenant, other_tenant):
        cache.set(tenant_cache_key(each, settings.PDF_CACHE_KEY), ["stale"], 60)

    superuser_client.post(reverse("pdf:templates:move"), move_payload(other_tenant, manual_template))

    for each in (tenant, other_tenant):
        assert cache.get(tenant_cache_key(each, settings.PDF_CACHE_KEY)) is None


def test_deleting_a_template_of_another_tenant_is_refused(staff_client, other_tenant):
    """A local admin cannot remove templates of another tenant."""
    foreign = ManualPDFTemplate.objects.create(tenant=other_tenant, name="Foreign", filename="foreign", locale="en")

    response = staff_client.post(reverse("pdf:templates:delete", kwargs={"pk": foreign.pk}))

    assert response.status_code == 404
    assert ManualPDFTemplate.objects.filter(pk=foreign.pk).exists()


@pytest.fixture(params=["manual", "category", "all_songs"])
def foreign_template(request, other_tenant, other_category):
    """A template of every kind, belonging to another tenant."""
    if request.param == "manual":
        return ManualPDFTemplate.objects.create(tenant=other_tenant, name="Foreign", filename="foreign", locale="en")
    if request.param == "category":
        return other_category
    return AllSongsTemplate.objects.create(tenant=other_tenant, filename="all-songs", locale="en")


def test_generating_from_a_template_of_another_tenant_is_refused(staff_client, foreign_template):
    """Files can only be generated from the templates of the tenant being served."""
    response = staff_client.get(reverse("pdf:templates:generate", kwargs={"pk": foreign_template.pk}))

    assert response.status_code == 404
    assert not PDFFile.objects.filter(template=foreign_template).exists()


def test_list_offers_generating_a_scheduled_file_now(staff_client, manual_template, make_pdf_file):
    """A template whose file waits for its time can be generated at once."""
    file = make_pdf_file(manual_template, status=Status.SCHEDULED)

    content = staff_client.get(reverse("pdf:templates:list")).content.decode()

    assert reverse("pdf:files:generate_now", kwargs={"pk": file.pk}) in content
