"""A song edit followed all the way to the PDF the readers download."""

import pytest
import weasyprint
from django.urls import reverse

from backend.models import Song
from pdf.models import Status
from pdf.models.request import PDFFile
from tenants.menu_items import distinct_requests

pytestmark = [pytest.mark.django_db, pytest.mark.slow]


@pytest.fixture
def rendered_html(monkeypatch):
    """Records the HTML handed to WeasyPrint, which still renders the real PDF"""
    pages = []
    real_html = weasyprint.HTML

    def recording_html(*args, **kwargs):
        pages.append(kwargs["string"])
        return real_html(*args, **kwargs)

    monkeypatch.setattr("pdf.generate.weasyprint.HTML", recording_html)
    return pages


@pytest.fixture(params=["pdf_category", "all_songs_template"])
def printed(request, pdf_category, all_songs_template, settings):
    """Each template an edit of a song in `pdf_category` generates a PDF for, without the delay"""
    settings.CATEGORY_PDF_DELAY = 0
    return request.getfixturevalue(request.param)


def test_editing_a_song_generates_the_pdf(staff_client, tenant, pdf_category, printed, rendered_html):
    """Saving a song produces a finished PDF that holds the song and is offered in the menu"""
    response = staff_client.post(
        reverse("backend:add"),
        {
            "name": "Campfire Song",
            "capo": 0,
            "author": "",
            "link": "",
            "text": "{C}Hello",
            "categories": [pdf_category.pk],
        },
    )

    assert response.status_code == 302
    song = Song.objects.get(name="Campfire Song")
    file = PDFFile.objects.get(template=printed)
    assert file.status == Status.DONE
    with file.file.open("rb") as stream:
        assert stream.read(4) == b"%PDF"
    assert "Campfire Song" in rendered_html[-1]
    assert song in [entry for _, entry in printed.get_songs()]
    assert file.name in [item["name"] for item in distinct_requests(tenant)]
