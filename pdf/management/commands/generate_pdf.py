"""Management command for generating PDF files from requests"""

import logging
from argparse import ArgumentParser
from pathlib import Path

from django.conf import settings
from django.core.management import BaseCommand

from category.models import Category
from pdf.generate import generate_pdf_file
from tenants.models import Tenant

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class Command(BaseCommand):
    """Generates PDF according to the PDF requests"""

    help = "Generates PDFs for all categories"

    def add_arguments(self, parser: ArgumentParser):
        parser.add_argument(
            "tenants",
            metavar="Tenants",
            type=int,
            nargs="+",
            default=[],
            help="Tenants IDs for which generate pdfs, if none specified, all tenants are considered",
        )

    # pylint: disable=too-many-locals
    def handle(self, *args, **options):
        Path(f"{settings.MEDIA_ROOT}/{settings.PDF_FILE_DIR}").mkdir(parents=True, exist_ok=True)
        tenants = set(options["tenants"])
        ids = set(Tenant.objects.filter(id__in=tenants).values_list("id", flat=True))
        diff = tenants - ids
        if diff:
            logger.error("Tenants with ids %s don't exists", diff)
            return

        queryset = Category.objects.filter(generate_pdf=True)
        if len(tenants) > 0:
            queryset = queryset.filter(tenant__id__in=tenants)

        for category in queryset:
            logger.info("Scheduling generation for category %s from Tenant %s", category, category.tenant.name)
        objects = [generate_pdf_file(category) for category in queryset]

        logger.info("Scheduled %i requests", len(objects))
        return
