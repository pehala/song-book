"""Utility functions for backend app"""
from django.conf import settings

from pdf.utils import request_pdf_regeneration


def regenerate_pdf(song):
    """Regenerates PDFs for each category song is in"""
    for category in song.categories.all():
        if category.generate_pdf:
            request_pdf_regeneration(category)


def regenerate_prerender(song):
    """Regenerates prerendered html for song"""
    if settings.USE_PRERENDERED_MARKDOWN:
        song.prerender_all()
