"""Models for PDF module"""

from collections.abc import Iterable

from django.core.validators import MinValueValidator
from django.db.models import (
    CASCADE,
    SET_NULL,
    BooleanField,
    CharField,
    DateTimeField,
    FileField,
    ForeignKey,
    IntegerField,
    ManyToManyField,
    Model,
    OneToOneField,
    PositiveIntegerField,
    TextChoices,
    UniqueConstraint,
)
from django.db.models.signals import post_delete
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

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
    return now().strftime(f"pdfs/{instance.tenant_id}/%y%m%d/{filename}")


class ManualPDFTemplate(PDFTemplate):
    """Template for creating PDF files. Used by users"""

    tenant = ForeignKey(Tenant, on_delete=CASCADE)
    songs = ManyToManyField(Song, through="PDFSong")
    name = CharField(_("Template Name"), help_text=_("Name of this template, only shown internally"), max_length=255)

    def get_songs(self) -> Iterable[tuple[int, Song]]:
        """Returns all songs for PDFTemplate"""
        return [
            (pdf_song.song_number, pdf_song.song)
            for pdf_song in PDFSong.objects.filter(request=self).select_related("song")
        ]

    class Meta:
        verbose_name = _("File Template")
        verbose_name_plural = _("File Templates")


class AllSongsTemplate(PDFTemplate):
    """Template of the PDF with every song of a Tenant, the printable counterpart of the all songs list"""

    tenant = OneToOneField(Tenant, on_delete=CASCADE)
    generate_pdf = BooleanField(
        verbose_name=_("PDF generation"),
        help_text=_("Check to generate the PDF file automatically when a song changes"),
        default=False,
    )

    @property
    def name(self):
        """Name shown wherever the template is listed"""
        return pgettext_lazy("all songs PDF template", "All Songs")

    def songs(self):
        """Non-archived songs of every category of the Tenant, in the order of the all songs list"""
        return Song.objects.filter(categories__tenant=self.tenant, archived=False).distinct()

    def get_songs(self) -> Iterable[tuple[int, Song]]:
        return list(enumerate(self.songs(), start=1))

    @classmethod
    def for_tenant(cls, tenant: Tenant, **defaults) -> AllSongsTemplate:
        """Returns the template of the Tenant, creating it with `defaults` on first use"""
        return cls.objects.get_or_create(tenant=tenant, defaults=defaults)[0]

    class Meta:
        verbose_name = _("All Songs PDF")
        verbose_name_plural = _("All Songs PDFs")


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
        help_text=_("Display name for the file, if empty, the file name will be used"),
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
        help_text=_("Check to make the file public"),
        verbose_name=_("Public file"),
    )

    @property
    def name(self):
        """Returns publicly visible name"""
        if self.display_name:
            return self.display_name
        return f"{self.filename}.pdf"

    @property
    def finished(self):
        """True, if file generation finished"""
        return self.status in [Status.DONE, Status.FAILED]

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
        constraints = [
            UniqueConstraint(fields=["song_number", "request", "song"], name="pdfsong_number_request_song_uniq"),
        ]
