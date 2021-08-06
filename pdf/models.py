"""Models for PDF module"""
from typing import List

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db.models import Model, DateField, DateTimeField, IntegerField, FileField, CharField, TextChoices, \
    ManyToManyField, ForeignKey, CASCADE, SET_NULL, CheckConstraint, Q, PositiveIntegerField, BooleanField, ImageField
from django.utils.translation import gettext_lazy as _

from backend.models import Song
from category.models import Category
from pdf.storage import DateOverwriteStorage


fs = DateOverwriteStorage()


class RequestType(TextChoices):
    """Type of PDF Request"""
    EVENT = 'EV', 'Automated'
    MANUAL = 'MA', 'Manual'


class Status(TextChoices):
    """Status of PDF Request"""
    QUEUED = "QU", 'Queued'
    IN_PROGRESS = "PR", 'In progress'
    DONE = "DO", "Done"
    FAILED = "FA", "Failed"


class PDFRequest(Model):
    """Request for PDF generation"""
    created_date = DateField(auto_now_add=True, editable=False)
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
    file = FileField(null=True, storage=fs)
    filename = CharField(max_length=30, null=True,
                         help_text=_("Filename of the generated PDF, please do not include .pdf"),
                         verbose_name=_("File name"))
    songs = ManyToManyField(Song, through="PDFSong")
    locale = CharField(choices=settings.LANGUAGES, verbose_name=_('Language'), max_length=5,
                       help_text=_("Language to be used in the generated PDF")
                       )
    category = ForeignKey(Category, null=True, on_delete=SET_NULL)
    name = CharField(max_length=100,
                     help_text=_("Name to be used on the title page of the PDF"),
                     verbose_name=_("Name"),
                     default=settings.SITE_NAME)
    show_date = BooleanField(default=True, verbose_name=_("Show date"),
                             help_text=_("True, if the date should be included in the final PDF"))
    image = ImageField(verbose_name=_("Title Image"),
                       help_text=_("Optional title image of the songbook"),
                       null=True,
                       blank=True,
                       upload_to='uploads/')

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
    song_number = PositiveIntegerField(validators=[MinValueValidator(1)])

    class Meta:
        unique_together = ['song_number', 'request', 'song']
