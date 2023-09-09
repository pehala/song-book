"""Utility functions"""
from datetime import timedelta
from django.utils import timezone

from django.db import transaction
from django.utils import translation
from django.utils.translation import gettext

from pdf.generate import schedule_generation
from pdf.models.request import PDFRequest, RequestType, Status, PDFSong


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
        PDFSong.objects.bulk_create([
            PDFSong(request=request,
                    song=song,
                    song_number=song_number + 1)
            for song_number, song in enumerate(category.song_set.filter(archived=False).all())
        ])
        return request


def generate_new_pdf_request(category):
    """Returns PDFRequest for a category"""
    with transaction.atomic():
        scheduled_times = PDFRequest.objects.filter(status=Status.SCHEDULED, type=RequestType.EVENT).values_list(
            'scheduled_at', flat=True)
        request = PDFRequest(type=RequestType.EVENT,
                             status=Status.SCHEDULED,
                             category=category)
        request.copy_options(category)
        request.filename = request.filename or get_filename(category)
        request.save()
        PDFSong.objects.bulk_create([
            PDFSong(request=request,
                    song=song,
                    song_number=song_number + 1)
            for song_number, song in enumerate(category.song_set.filter(archived=False).all())
        ])

        time = generate_unique_time(scheduled_times, timedelta(minutes=30))

        schedule_generation(request, time)
        request.scheduled_at = time
        request.save()

        return request

def generate_unique_time(times, delta: timedelta):
    """Generate unique time, so jobs will not clash on scheduler"""
    time = timezone.now() + delta
    for _ in range(len(times) + 1):

        valid = True
        for existing_time in times:
            if not existing_time:
                continue
            if time - existing_time < delta:
                valid = False

        if valid:
            return time
        time = time + delta
    raise AttributeError("Unable to assign unique generation time")

def get_filename(category):
    """Returns filename for category based on its locale"""
    with translation.override(category.locale):
        text = gettext('songbook')
        return f"{text}-{category.name}"
