"""Module containing all things related to generating PDF"""
import locale
import logging
import os
import re
import tempfile
from datetime import datetime
from math import ceil
from time import time

import weasyprint
from rq import Retry
from weasyprint.logger import PROGRESS_LOGGER
from django.conf import settings
from django.core.files import File
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import translation
from django_rq import job, get_queue
from django_weasyprint.utils import django_url_fetcher

from pdf.locales import changed_locale, lang_to_locale
from pdf.models.request import PDFRequest, Status

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def update_status(request: PDFRequest, status: Status):
    """Updates status of the request if it is in DB"""
    request.status = status
    request.save()


def get_base_url():
    """
    Determine base URL to fetch CSS files from `WEASYPRINT_BASEURL` or
    fall back to using the root path of the URL used in the request.
    """
    return getattr(settings, "WEASYPRINT_BASEURL", reverse("chords:index"))


def generate_pdf(request: PDFRequest):
    """Generates PDF"""
    songs = sorted(request.get_songs(), key=lambda song: song.song_number)
    with changed_locale(lang_to_locale(request.locale)):
        sorted_songs = sorted(songs, key=lambda song: locale.strxfrm(song.name))

    update_status(request, Status.IN_PROGRESS)

    timer = Timer()
    try:
        rel_path = f"{settings.PDF_FILE_DIR}/{request.filename}.pdf"
        with tempfile.TemporaryFile(mode="a+b") as file:
            with translation.override(request.locale), timer:
                name = os.path.basename(rel_path)
                logger.info("Generating %s", name)
                logger.debug("from request %s", request)
                string = render_to_string(
                    template_name="pdf/index.html",
                    context={
                        "songs": songs,
                        "sorted_songs": sorted_songs,
                        "name": request.title or request.tenant.display_name,
                        "request": request,
                        "link": request.link,
                    },
                )
                PROGRESS_LOGGER.setLevel(logging.INFO)
                log_filter = ProgressFilter(request)
                PROGRESS_LOGGER.addFilter(log_filter)
                weasyprint.HTML(
                    string=string,
                    url_fetcher=django_url_fetcher,
                    base_url=get_base_url(),
                ).write_pdf(file, optimize_size=("fonts", "images"))
                PROGRESS_LOGGER.removeFilter(log_filter)
            request.file.save(rel_path, File(file, name=rel_path))
            request.time_elapsed = ceil(timer.duration)

            update_status(request, Status.DONE)
            logger.info("Done in %i seconds", request.time_elapsed)
            return True, timer.duration
    except Exception as exception:  # pylint: disable=broad-except
        logger.error("Request failed: %s", str(exception))
        update_status(request, Status.FAILED)
        return False, timer.duration


@job
def generate_pdf_job(request: PDFRequest):
    """Generates PDF from request in the background"""
    generate_pdf(request)


def schedule_generation(request: PDFRequest, schedule_time: datetime):
    """Schedules generation of a request at a specific time"""
    queue = get_queue("default")
    created_job = queue.enqueue_at(schedule_time, generate_pdf, request, retry=Retry(max=5, interval=120))
    logger.info("Schedule PDF generation of request %s at %s", request.id, schedule_time)
    return created_job


class ProgressFilter(logging.Filter):
    """Filters Weasyprint progress messages, highly dependent on implementation!"""

    STEP_NUMBER = re.compile(r"(?<=Step\s)\d")

    def __init__(self, request):
        super().__init__()
        self.request = request

    def filter(self, record):
        step = self.STEP_NUMBER.search(record.getMessage()).group(0)
        if self.request.progress != step:
            self.request.progress = step
            self.request.save()
        return True


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
