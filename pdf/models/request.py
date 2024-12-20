"""Models for PDF module"""

from datetime import datetime
from typing import Iterable, Tuple

from django.core.validators import MinValueValidator
from django.db.models import (
    Model,
    DateTimeField,
    IntegerField,
    FileField,
    CharField,
    TextChoices,
    ManyToManyField,
    ForeignKey,
    CASCADE,
    PositiveIntegerField,
    BooleanField,
    SET_NULL,
)
from django.db.models.signals import post_delete
from django.utils.translation import gettext_lazy as _

from backend.models import Song
from pdf.models import PDFTemplate, Status
from pdf.storage import file_cleanup
from tenants.models import Tenant


class RequestType(TextChoices):
    """Type of PDF Request"""

    EVENT = "EV", _("Automated")
    MANUAL = "MA", _("Manual")


def upload_path(instance, filename):
    """Returns upload path for this request"""
    return datetime.now().strftime(f"pdfs/{instance.tenant_id}/%y%m%d/{filename}")


class ManualPDFTemplate(PDFTemplate):
    """Template for creating PDF files. Used by users"""

    tenant = ForeignKey(Tenant, on_delete=CASCADE)
    songs = ManyToManyField(Song, through="PDFSong")
    name = CharField(_("Template Name"), help_text=_("Name of this template, only shown internally"), max_length=255)

    def get_songs(self) -> Iterable[Tuple[int, "Song"]]:
        """Returns all songs for PDFTemplate"""
        return [(pdf_song.song_number, pdf_song.song) for pdf_song in PDFSong.objects.filter(request=self)]

    class Meta:
        verbose_name = _("File Template")
        verbose_name_plural = _("File Templates")


class PDFFile(Model):
    """PDF File, that is either already generated or await generation"""

    template = ForeignKey(PDFTemplate, on_delete=SET_NULL, null=True)
    tenant = ForeignKey(Tenant, on_delete=CASCADE)

    filename = CharField(
        max_length=30,
        blank=False,
        null=False,
        help_text=_("File name of the generated PDF"),
        verbose_name=_("File name"),
    )
    display_name = CharField(
        max_length=30,
        null=True,
        blank=True,
        help_text=_("Display name for the file, if empty filename will be used"),
        verbose_name=_("Display name"),
    )
    update_date = DateTimeField(null=True)
    status = CharField(max_length=2, choices=Status.choices, default=Status.QUEUED)
    time_elapsed = IntegerField(null=True)
    progress = IntegerField(default=0)
    file = FileField(null=True, upload_to=upload_path)
    scheduled_at = DateTimeField(null=True)
    public = BooleanField(
        default=True,
        help_text=_("True, if the file should be public"),
        verbose_name=_("Public file"),
    )

    @property
    def name(self):
        """Returns publicly visible name"""
        if self.display_name:
            return self.display_name
        return f"{self.filename}.pdf"

    class Meta:
        verbose_name = _("File")
        verbose_name_plural = _("Files")
        ordering = ["-update_date"]


post_delete.connect(file_cleanup, sender=PDFFile, dispatch_uid="pdffile.file_cleanup")


class PDFSong(Model):
    """Through table for PDFRequest and Song"""

    song = ForeignKey(Song, on_delete=CASCADE)
    request = ForeignKey(ManualPDFTemplate, on_delete=CASCADE)
    song_number = PositiveIntegerField(validators=[MinValueValidator(1)], verbose_name=_("Song number"))

    class Meta:
        unique_together = ["song_number", "request", "song"]
