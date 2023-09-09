"""Management command for generating PDF files from requests"""
import logging
from argparse import ArgumentParser
from math import ceil
from pathlib import Path

from django.conf import settings
from django.core.cache import cache
from django.core.management import BaseCommand

from category.models import Category
from pdf.generate import generate_pdf
from pdf.models.request import PDFRequest, Status
from pdf.utils import generate_new_pdf_request

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


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
        all_requests = options["all"]
        requests = options["requests"]
        total_duration = 0

        if all_requests:
            objects = [generate_new_pdf_request(category) for category in Category.objects.filter(generate_pdf=True)]
        else:
            objects = PDFRequest.objects.filter(status__in={Status.QUEUED, Status.SCHEDULED})
            if requests:
                objects = objects[:requests]

        num = len(objects)
        if num == 0:
            logger.info("No requests, skipping")
            return

        for request in objects:
            _, time = generate_pdf(request)
            total_duration += time

        cache.delete(settings.PDF_CACHE_KEY)
        logger.info("Processed %i requests in %i seconds", num, ceil(total_duration))
        return
