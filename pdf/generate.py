"""Module containing all things related to generating PDF."""

import locale
import logging
import os
import re
import tempfile
from datetime import timedelta
from math import ceil
from time import time

import weasyprint
from django.conf import settings
from django.core.cache import cache
from django.core.files import File
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import translation
from django.utils.timezone import now
from django_weasyprint.utils import DjangoURLFetcher
from huey.contrib.djhuey import task
from weasyprint.logger import PROGRESS_LOGGER

from category.models import Category
from pdf.locales import changed_locale, lang_to_locale
from pdf.models.request import AllSongsTemplate, ManualPDFTemplate, PDFFile, Status
from tenants.utils import tenant_cache_key

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

AllowedTemplates = Category | ManualPDFTemplate | AllSongsTemplate

# Number of columns of the table of contents; the `columns` of `.contents-list` in pdf.css must match
CONTENTS_COLUMNS = 3


def update_status(file: PDFFile, status: Status):
    """Updates status of the request if it is in DB."""
    file.status = status
    file.save()


def get_base_url():
    """Determines the base URL to fetch CSS files from.

    It is `WEASYPRINT_BASEURL`, falling back to the root path of the URL used in the request.
    """
    return getattr(settings, "WEASYPRINT_BASEURL", reverse("chords:index"))


def generate_pdf(pdf_file: PDFFile, template: AllowedTemplates):
    """Generates PDF."""
    sections = template.get_sections()
    with changed_locale(lang_to_locale(template.locale)):
        contents = [
            (section, sorted(section.songs, key=lambda numbered: locale.strxfrm(numbered[1].name)))
            for section in sections
        ]

    update_status(pdf_file, Status.IN_PROGRESS)

    timer = Timer()
    try:
        rel_path = f"{settings.PDF_FILE_DIR}/{template.filename}.pdf"
        with tempfile.TemporaryFile(mode="a+b") as tmp_file:
            with translation.override(template.locale), timer:
                name = os.path.basename(rel_path)
                logger.info("Generating %s", name)
                logger.debug("from Template %s", template)
                string = render_to_string(
                    template_name="pdf/index.html",
                    context={
                        "sections": sections,
                        "contents": contents,
                        "contents_columns": range(CONTENTS_COLUMNS),
                        "name": template.title or template.tenant.display_name,
                        "request": template,
                        "link_url": template.link_url,
                    },
                )
                PROGRESS_LOGGER.setLevel(logging.INFO)
                log_filter = ProgressFilter(pdf_file)
                PROGRESS_LOGGER.addFilter(log_filter)
                weasyprint.HTML(
                    string=string,
                    url_fetcher=DjangoURLFetcher(),
                    base_url=get_base_url(),
                ).write_pdf(tmp_file, optimize_images=True)
                PROGRESS_LOGGER.removeFilter(log_filter)
            pdf_file.file.save(rel_path, File(tmp_file, name=rel_path))
            pdf_file.time_elapsed = ceil(timer.duration)
            pdf_file.update_date = now()

            update_status(pdf_file, Status.DONE)
            cache.delete(tenant_cache_key(pdf_file.tenant, settings.PDF_CACHE_KEY))
            logger.info("Done in %i seconds", pdf_file.time_elapsed)
            return True, timer.duration
    except Exception as exception:  # noqa: BLE001
        logger.error("Request failed: %s", str(exception))
        update_status(pdf_file, Status.FAILED)
        return False, timer.duration


@task()
def generate_pdf_job(file: PDFFile, template: AllowedTemplates):
    """Generates PDF from request in the background, unless the file is no longer scheduled.

    A file is taken over by the first job that finds it scheduled, so a file generated at once by `generate_file_now`
    is not generated again when its original job comes due, and a file deleted before its job starts is not generated.
    """
    if not PDFFile.objects.filter(pk=file.pk, status=Status.SCHEDULED).update(status=Status.IN_PROGRESS):
        logger.info("Skipping file %s, it is not scheduled", file.pk)
        return
    file.refresh_from_db()
    generate_pdf(file, template)


def generate_pdf_file(template: AllowedTemplates, delay: int = 0):
    """Schedules generation of a request at a specific time."""
    current_time = now()
    scheduled_time = current_time + timedelta(seconds=delay)
    file = PDFFile.objects.create(
        template=template,
        status=Status.SCHEDULED,
        tenant=template.tenant,
        update_date=current_time,
        scheduled_at=scheduled_time,
        public=template.public,
        filename=template.filename,
        display_name=template.display_name,
    )
    generate_pdf_job.schedule(kwargs={"file": file, "template": template}, eta=scheduled_time)

    # queue = get_queue("default")
    # created_job = queue.enqueue_at(schedule_time, generate_pdf, request, retry=Retry(max=5, interval=120))
    if delay > 0:
        logger.info("Scheduled PDF generation of file %s from template %s in %s seconds", file.id, template.name, delay)
    else:
        logger.info("Scheduled File (%s) generation from template %s", file.id, template.name)
    return file


def generate_file_now(file: PDFFile):
    """Generates a scheduled file now instead of at its scheduled time, returns False if it cannot be."""
    template = file.template
    if file.status != Status.SCHEDULED or template is None:
        return False
    file.scheduled_at = now()
    file.save(update_fields=["scheduled_at"])
    generate_pdf_job(file, template)
    logger.info("Generating scheduled file %s from template %s", file.id, template.name)
    return True


class ProgressFilter(logging.Filter):
    """Filters Weasyprint progress messages, highly dependent on implementation!"""

    STEP_NUMBER = re.compile(r"(?<=Step\s)\d")

    def __init__(self, file):
        super().__init__()
        self.file = file

    def filter(self, record):
        """Stores the step WeasyPrint reports as the progress of the file."""
        step = self.STEP_NUMBER.search(record.getMessage()).group(0)
        if self.file.progress != step:
            self.file.progress = step
            self.file.save()
        return True


class Timer:
    """Context manager for measuring time."""

    def __init__(self):
        self.duration = 0
        self.start = 0
        self.end = 0

    def __enter__(self):
        self.start = time()

    def __exit__(self, exit_type, value, traceback):
        self.end = time()
        self.duration = self.end - self.start
