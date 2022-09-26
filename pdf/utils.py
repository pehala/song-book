"""Utility functions"""
from time import time

from django.conf import settings
from django.db import transaction
from django.utils import translation
from django.utils.translation import gettext

from pdf.models.request import PDFRequest, RequestType, Status, PDFSong


def request_pdf_regeneration(category, update: bool = False):
    """Requests automatic PDF regeneration if none is pending"""
    objects = PDFRequest.objects.filter(type=RequestType.EVENT, status=Status.QUEUED, category=category)
    if not objects.exists():
        generate_new_pdf_request(category)
    elif not update:
        regenerate_pdf_request(objects.first(), category)


def regenerate_pdf_request(request, category):
    """Regenerates the PDF request with newest info"""
    with transaction.atomic():
        PDFSong.objects.filter(request=request).delete()
        PDFSong.objects.bulk_create([
            PDFSong(request=request,
                    song=song,
                    song_number=song_number + 1)
            for song_number, song in enumerate(category.song_set.filter(archived=False).all())
        ])
        return request


def generate_new_pdf_request(category):
    """Returns PDFRequest for basic"""
    with transaction.atomic():
        request = PDFRequest(type=RequestType.EVENT,
                             status=Status.QUEUED,
                             category=category)
        request.copy_options(category)
        request.filename = request.title or get_filename(category)
        request.save()
        PDFSong.objects.bulk_create([
            PDFSong(request=request,
                    song=song,
                    song_number=song_number + 1)
            for song_number, song in enumerate(category.song_set.filter(archived=False).all())
        ])
        return request


def get_filename(category):
    """Returns filename for category based on its locale"""
    with translation.override(category.locale):
        text = gettext('songbook')
        return f"{text}-{category.name}"


def get_name(category):
    """Returns filename for category based on its locale"""
    with translation.override(category.locale):
        return gettext(settings.SITE_NAME)


class Timer:
    """Context manager for measuring time"""
    def __init__(self):
        self.duration = 0
        self.start = 0
        self.end = 0

    def __enter__(self):
        self.start = time()

    def __exit__(self, exit_type, value, traceback):
        self.end = time()
        self.duration = self.end - self.start
