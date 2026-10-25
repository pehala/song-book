"""Models for PDF module."""

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
from pdf.models import PDFTemplate, Section, Status, group_sections
from pdf.storage import file_cleanup
from tenants.models import Tenant


class RequestType(TextChoices):
    """Type of PDF Request."""

    EVENT = "EV", _("Automated")
    MANUAL = "MA", _("Manual")


def upload_path(instance, filename):
    """Returns upload path for this request."""
    return now().strftime(f"pdfs/{instance.tenant_id}/%y%m%d/{filename}")


class ManualPDFTemplate(PDFTemplate):
    """Template for creating PDF files. Used by users."""

    tenant = ForeignKey(Tenant, on_delete=CASCADE)
    songs = ManyToManyField(Song, through="PDFSong")
    name = CharField(_("Template Name"), help_text=_("Name of this template, only shown internally"), max_length=255)

    def get_sections(self) -> list[Section]:
        """The songs in the order of their numbers, divided into the sections they are labelled with."""
        return group_sections(
            (pdf_song.song_number, pdf_song.song, pdf_song.section)
            for pdf_song in PDFSong.objects.filter(request=self).select_related("song").order_by("song_number")
        )

    def get_songs(self) -> Iterable[tuple[int, Song]]:
        """Returns all songs for PDFTemplate."""
        return [numbered for section in self.get_sections() for numbered in section.songs]

    class Meta:
        verbose_name = _("File Template")
        verbose_name_plural = _("File Templates")


def category_rows(tenant: Tenant, songs: Iterable[Song]) -> list[tuple[int, Song, str]]:
    """Numbers the songs one after another through the Categories of the Tenant, in the order they were made.

    Each song is under the first Category it is in and, within a Category, in the order it was given. Every row
    carries the name of its Category; a song in no Category of the Tenant is left out.
    """
    songs = list(songs)
    links = (
        Song.categories.through.objects.filter(song__in=songs, category__tenant=tenant)
        .order_by("category_id")
        .values_list("song_id", "category_id", "category__name")
    )
    first = {}
    for song_id, category_id, name in links:
        first.setdefault(song_id, (category_id, name))
    placed = sorted((song for song in songs if song.pk in first), key=lambda song: first[song.pk][0])
    return [(number, song, first[song.pk][1]) for number, song in enumerate(placed, start=1)]


class AllSongsTemplate(PDFTemplate):
    """Template of the PDF with every song of a Tenant, the printable counterpart of the all songs list."""

    tenant = OneToOneField(Tenant, on_delete=CASCADE)
    generate_pdf = BooleanField(
        verbose_name=_("PDF generation"),
        help_text=_("Check to generate the PDF file automatically when a song changes"),
        default=False,
    )
    category_sections = BooleanField(
        verbose_name=_("Sections by category"),
        help_text=_("True, if the songs should be divided into a section for each category"),
        default=False,
    )

    @property
    def name(self):
        """Name shown wherever the template is listed."""
        return pgettext_lazy("all songs PDF template", "All Songs")

    def songs(self):
        """Non-archived songs of every category of the Tenant, in the order of the all songs list."""
        return Song.objects.filter(categories__tenant=self.tenant, archived=False).distinct()

    def get_songs(self) -> Iterable[tuple[int, Song]]:
        """Returns the numbered songs of the template."""
        return list(enumerate(self.songs(), start=1))

    def get_sections(self) -> list[Section]:
        """Returns one section per Category of the Tenant, or a single one without `category_sections`.

        Each song is in the first Category it is in. The songs are numbered one after another and, within a
        Category, in the order of its list.
        """
        if not self.category_sections:
            return super().get_sections()
        return group_sections(category_rows(self.tenant, self.songs()))

    @classmethod
    def for_tenant(cls, tenant: Tenant, **defaults) -> AllSongsTemplate:
        """Returns the template of the Tenant, creating it with `defaults` on first use."""
        return cls.objects.get_or_create(tenant=tenant, defaults=defaults)[0]

    class Meta:
        verbose_name = _("All Songs PDF")
        verbose_name_plural = _("All Songs PDFs")


class PDFFile(Model):
    """PDF File, that is either already generated or await generation."""

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
        """Returns publicly visible name."""
        if self.display_name:
            return self.display_name
        return f"{self.filename}.pdf"

    @property
    def finished(self):
        """True, if file generation finished."""
        return self.status in [Status.DONE, Status.FAILED]

    class Meta:
        verbose_name = _("File")
        verbose_name_plural = _("Files")
        ordering = ["-update_date"]


post_delete.connect(file_cleanup, sender=PDFFile, dispatch_uid="pdffile.file_cleanup")


class PDFSong(Model):
    """Through table for PDFRequest and Song."""

    song = ForeignKey(Song, on_delete=CASCADE)
    request = ForeignKey(ManualPDFTemplate, on_delete=CASCADE)
    song_number = PositiveIntegerField(validators=[MinValueValidator(1)], verbose_name=_("Song number"))
    section = CharField(
        max_length=100,
        blank=True,
        help_text=_("Title of the section the song starts or continues, empty for none"),
        verbose_name=_("Section"),
    )

    class Meta:
        constraints = [
            UniqueConstraint(fields=["song_number", "request", "song"], name="pdfsong_number_request_song_uniq"),
        ]
