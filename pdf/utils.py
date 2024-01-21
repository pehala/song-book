"""Utility functions"""

import logging
from datetime import timedelta

from django.utils.timezone import now

from pdf.generate import schedule_generation
from pdf.models.request import Status

log = logging.getLogger(__name__)


def request_pdf_regeneration(category):
    """Requests automatic PDF regeneration if none is pending"""
    request = category.request
    if request.status == Status.DONE:
        request.status = Status.SCHEDULED
        schedule_generation(request, 30 * 60)
        request.scheduled_at = now() + timedelta(minutes=30)
        request.save()
