"""Models for PDF module"""
from django.conf import settings
from django.db import models

from django.db.models import Model, DateField, CharField, DateTimeField, IntegerField
from django.utils.translation import gettext_lazy as _

from backend.models import Song


class RequestType(models.TextChoices):
    """Type of PDF Request"""
    EVENT = 'EV', 'Automated'
    MANUAL = 'MA', 'Manual'


class Status(models.TextChoices):
    """Status of PDF Request"""
    QUEUED = "QU", 'Queued'
    IN_PROGRESS = "PR", 'In progress'
    DONE = "DO", "Done"
    FAILED = "ER", "Failed"


class PDFRequest(Model):
    """Request for PDF generation"""
    created_date = DateField(auto_now_add=True, editable=False)
    update_date = DateTimeField(auto_now=True)
    locale = CharField(choices=settings.LANGUAGES, verbose_name=_('Language'), max_length=5)
    type = models.CharField(
        max_length=2,
        choices=RequestType.choices,
        default=RequestType.EVENT,
    )
    status = models.CharField(
        max_length=2,
        choices=Status.choices,
        default=Status.QUEUED
    )
    time_elapsed = IntegerField(null=True)
    filename = CharField(max_length=30, null=True)
    songs = models.ManyToManyField(Song)
