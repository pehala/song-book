"""Utility functions"""

from django.conf import settings

from pdf.generate import generate_pdf_file
from pdf.models.request import AllSongsTemplate


def request_pdf_regeneration(template):
    """Requests automatic PDF regeneration if none is pending"""
    if template.generate_pdf and not template.has_scheduled_file():
        generate_pdf_file(template, settings.CATEGORY_PDF_DELAY)


def request_all_songs_pdf_regeneration(tenant):
    """Requests automatic regeneration of the all songs PDF, which only exists while the all songs list does"""
    template = AllSongsTemplate.objects.filter(tenant=tenant).first()
    if template and tenant.all_songs_category:
        request_pdf_regeneration(template)
