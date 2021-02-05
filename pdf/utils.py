"""Utility functions"""
from time import time

from django.db import transaction
from django.utils import translation
from django.utils.translation import gettext

from pdf.models import PDFRequest, RequestType, Status, PDFSong


def request_pdf_regeneration(category):
    """Requests automatic PDF regeneration if none is pending"""
    if not PDFRequest.objects.filter(type=RequestType.EVENT, status=Status.QUEUED, category=category).exists():
        generate_pdf_request(category)


def generate_pdf_request(category):
    """Returns PDFRequest for basic"""
    with transaction.atomic():
        request = PDFRequest(type=RequestType.EVENT,
                             status=Status.QUEUED,
                             category=category,
                             filename=get_filename(category),
                             locale=category.locale)
        request.save()
        PDFSong.objects.bulk_create([
            PDFSong(request=request,
                    song=song,
                    song_number=song_number + 1)
            for song_number, song in enumerate(category.song_set.all())
        ])
        return request


def get_filename(category):
    """Returns filename for category based on its locale"""
    with translation.override(category.locale):
        text = gettext('songbook')
        return f"{text}-{category.name}"


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
