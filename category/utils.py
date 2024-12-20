"""Utility functions"""

from django.conf import settings

from pdf.generate import generate_pdf_file


def request_pdf_regeneration(category):
    """Requests automatic PDF regeneration if none is pending"""
    if category.generate_pdf and not category.has_scheduled_file():
        generate_pdf_file(category, settings.CATEGORY_PDF_DELAY)
