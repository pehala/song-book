"""Management command for generating PDF files from requests"""
import logging
import os
import tempfile
from argparse import ArgumentParser
from math import ceil
from pathlib import Path

import weasyprint
from django.conf import settings
from django.core.files import File
from django.core.management import BaseCommand
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import translation
from django_weasyprint.utils import django_url_fetcher

from category.models import Category
from pdf.models import PDFRequest, Status
from pdf.utils import Timer, generate_pdf_request

TEMPLATE = "pdf/index.html"

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def update_status(request: PDFRequest, status: Status, generate_all=False):
    """Updates status of the request if it is in DB"""
    if not generate_all:
        request.status = status
        request.save()


def get_base_url():
    """
    Determine base URL to fetch CSS files from `WEASYPRINT_BASEURL` or
    fall back to using the root path of the URL used in the request.
    """
    return getattr(
        settings, 'WEASYPRINT_BASEURL',
        reverse("chords:index")
    )


class Command(BaseCommand):
    """Generates PDF according to the PDF requests"""
    help = 'Generates PDFs that were requested'

    def add_arguments(self, parser: ArgumentParser):
        parser.add_argument('requests',
                            metavar='Requests',
                            type=int,
                            nargs='?',
                            default="0",
                            help="Number of requests to process, will process all requests if not value is specified")
        parser.add_argument('--all',
                            action='store_true',
                            help="Regenerates PDF for all categories")

    # pylint: disable=too-many-locals
    def handle(self, *args, **options):
        Path(f"{settings.MEDIA_ROOT}/{settings.PDF_FILE_DIR}").mkdir(parents=True, exist_ok=True)
        total_duration = 0
        generate_all = options["all"]

        if generate_all:
            objects = [generate_pdf_request(category) for category in Category.objects.filter(generate_pdf=True)]
        else:
            objects = PDFRequest.objects.filter(status=Status.QUEUED)
            if options["requests"] > 0:
                objects = objects[:options["requests"]]

        num = len(objects)
        if num == 0:
            return "No requests, doing nothing"

        for request in objects:
            songs = request.get_songs()
            sorted_songs = sorted(songs, key=lambda song: song.name)

            update_status(request, Status.IN_PROGRESS, generate_all)

            try:
                timer = Timer()
                rel_path = f"{settings.PDF_FILE_DIR}/{request.filename}.pdf"
                with tempfile.TemporaryFile(mode="a+b") as file:
                    with translation.override(request.locale), timer:
                        name = os.path.basename(rel_path)
                        logger.info("Generating %s", name)
                        logger.debug("from request %s", request)
                        string = render_to_string(template_name=TEMPLATE, context={
                            "songs": songs,
                            "sorted_songs": sorted_songs,
                            "name": request.name or "Jerry's songs"
                        })
                        weasyprint.HTML(
                            string=string,
                            url_fetcher=django_url_fetcher,
                            base_url=get_base_url()
                        ).write_pdf(file)
                    request.file.save(rel_path, File(file, name=rel_path))
                    total_duration += timer.duration
                    request.time_elapsed = ceil(timer.duration)

                    update_status(request, Status.DONE, generate_all)
                    logger.info("Done in %i seconds", request.time_elapsed)

            # pylint: disable=broad-except
            except Exception as exception:
                logger.error("Request failed: %s", str(exception))
                update_status(request, Status.FAILED, generate_all)

        return f"Processed {num} requests in {ceil(total_duration)} seconds"
