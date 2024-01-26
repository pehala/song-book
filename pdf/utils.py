"""Utility functions"""

import logging
from datetime import timedelta

from django.db import transaction
from django.utils import translation
from django.utils.timezone import now
from django.utils.translation import gettext

from pdf.generate import schedule_generation
from pdf.models.request import PDFRequest, RequestType, Status, PDFSong

log = logging.getLogger(__name__)


def request_pdf_regeneration(category, update: bool = False):
    """Requests automatic PDF regeneration if none is pending"""
    objects = PDFRequest.objects.filter(type=RequestType.EVENT, status=Status.SCHEDULED, category=category)
    if not objects.exists():
        generate_new_pdf_request(category)
    elif not update:
        regenerate_pdf_request(objects.first(), category)


def regenerate_pdf_request(request, category):
    """Regenerates the PDF request with the newest info"""
    with transaction.atomic():
        PDFSong.objects.filter(request=request).delete()
        PDFSong.objects.bulk_create(
            [
                PDFSong(request=request, song=song, song_number=song_number + 1)
                for song_number, song in enumerate(category.song_set.filter(archived=False).all())
            ]
        )
        return request


def generate_new_pdf_request(category, force_now=False):
    """Returns PDFRequest for a category"""
    with transaction.atomic():
        request = PDFRequest(type=RequestType.EVENT, status=Status.SCHEDULED, category=category, tenant=category.tenant)
        request.copy_options(category)
        request.filename = request.filename or get_filename(category)
        request.save()
        PDFSong.objects.bulk_create(
            [
                PDFSong(request=request, song=song, song_number=song_number + 1)
                for song_number, song in enumerate(category.song_set.filter(archived=False).all())
            ]
        )

        if force_now:
            job = schedule_generation(request, 0)
            request.scheduled_at = now()
        else:
            job = schedule_generation(request, 30 * 60)
            request.scheduled_at = now() + timedelta(minutes=30)
        request.save()

        return request, job


def get_filename(category):
    """Returns filename for category based on its locale"""
    with translation.override(category.locale):
        text = gettext("songbook")
        return f"{text}-{category.name}"
