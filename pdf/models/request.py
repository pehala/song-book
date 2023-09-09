"""Models for PDF module"""
from typing import List

from django.core.validators import MinValueValidator
from django.db.models import Model, DateField, DateTimeField, IntegerField, FileField, CharField, TextChoices, \
    ManyToManyField, ForeignKey, CASCADE, SET_NULL, CheckConstraint, Q, PositiveIntegerField, TextField
from django.utils.translation import gettext_lazy as _

from backend.models import Song
from category.models import Category
from pdf.models import PDFOptions
from pdf.storage import DateOverwriteStorage

fs = DateOverwriteStorage()


class RequestType(TextChoices):
    """Type of PDF Request"""
    EVENT = 'EV', _('Automated')
    MANUAL = 'MA', _('Manual')


class Status(TextChoices):
    """Status of PDF Request"""
    QUEUED = "QU", _('Queued')
    SCHEDULED = "SC", _('Scheduled')
    IN_PROGRESS = "PR", _('In progress')
    DONE = "DO", _("Done")
    FAILED = "FA", _("Failed")


class PDFRequest(PDFOptions):
    """Request for PDF generation"""
#    created_date = DateField(auto_now_add=True, editable=False)
    update_date = DateTimeField(auto_now=True)
    type = CharField(
        max_length=2,
        choices=RequestType.choices,
        default=RequestType.EVENT,
    )
    status = CharField(
        max_length=2,
        choices=Status.choices,
        default=Status.QUEUED
    )
    time_elapsed = IntegerField(null=True)
    progress = IntegerField(default=0)
    file = FileField(null=True, storage=fs)
    songs = ManyToManyField(Song, through="PDFSong")
    category = ForeignKey(Category, null=True, on_delete=SET_NULL)
    scheduled_at = DateTimeField(null=True)

    def get_songs(self) -> List[Song]:
        """Returns all songs for request"""
        return [transform_song(pdf_song) for pdf_song in PDFSong.objects.filter(request=self)]

    class Meta:
        constraints = [
            CheckConstraint(check=Q(type=RequestType.MANUAL) | Q(category__isnull=False),
                            name='automated_category_present'),
        ]
        ordering = ["-update_date"]


def transform_song(pdf_song: 'PDFSong') -> Song:
    """Mapping function that maps PDFSong into Song"""
    song = pdf_song.song
    song.song_number = pdf_song.song_number
    return song


class PDFSong(Model):
    """Through table for PDFRequest and Song"""
    song = ForeignKey(Song, on_delete=CASCADE)
    request = ForeignKey(PDFRequest, on_delete=CASCADE)
    song_number = PositiveIntegerField(validators=[MinValueValidator(1)], verbose_name=_("Song number"))

    class Meta:
        unique_together = ['song_number', 'request', 'song']
