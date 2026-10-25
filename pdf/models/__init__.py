"""Common classes for PDF."""

import re
from abc import abstractmethod
from collections.abc import Iterable
from dataclasses import dataclass
from itertools import groupby
from typing import TYPE_CHECKING

from django.conf import settings
from django.db.models import BooleanField, CharField, FloatField, ImageField, TextChoices
from django.db.models.signals import post_delete
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy
from polymorphic.models import PolymorphicModel

from pdf.storage import file_cleanup

if TYPE_CHECKING:
    from backend.models import Song

    from .request import PDFFile

# A link that names its scheme, such as https://example.org or mailto:someone@example.org
LINK_SCHEME_RE = re.compile(r"[a-z][a-z0-9+.-]*://|mailto:", re.IGNORECASE)


@dataclass
class Section:
    """A titled run of songs of a PDF; the song numbers are those of the whole PDF."""

    title: str | None
    songs: list[tuple[int, Song]]


# Title of a section without one that follows a titled one, whose songs would otherwise look like its own
OTHER_SECTION = pgettext_lazy("title of the songs outside the sections", "Other")


def group_sections(rows: Iterable[tuple[int, Song, str]]) -> list[Section]:
    """Groups numbered songs, each with the label of its section, into sections: a run of one label is a section.

    Only the first section may be untitled; a later one without a label is titled "Other".
    """
    sections = [
        Section(title or None, [(number, song) for number, song, _title in run])
        for title, run in groupby(rows, key=lambda row: row[2])
    ]
    for section in sections[1:]:
        section.title = section.title or OTHER_SECTION
    return sections


class Status(TextChoices):
    """Status of PDF Request."""

    QUEUED = "QU", _("Queued")
    SCHEDULED = "SC", _("Scheduled")
    IN_PROGRESS = "PR", _("In progress")
    DONE = "DO", _("Done")
    FAILED = "FA", _("Failed")


class PDFTemplate(PolymorphicModel):
    """All options for PDF Generation in a form of an abstract model."""

    display_name = CharField(
        max_length=30,
        null=True,
        blank=True,
        help_text=_("(Optional) Display name for the generated files. If empty, the file name will be used"),
        verbose_name=_("Display name"),
    )
    filename = CharField(
        max_length=30,
        blank=False,
        null=False,
        help_text=_("File name of the generated PDF"),
        verbose_name=_("File name"),
    )
    public = BooleanField(
        default=True,
        help_text=_("Check to show the file in the menu"),
        verbose_name=_("Public file"),
    )
    locale = CharField(
        choices=settings.LANGUAGES,
        verbose_name=_("Language"),
        max_length=5,
        help_text=_("Language of the generated PDF"),
    )
    title = CharField(
        max_length=100,
        blank=True,
        help_text=_("Name for the title page of the PDF, usually only this or the title image is needed"),
        verbose_name=_("Title"),
    )
    show_date = BooleanField(
        default=True,
        verbose_name=_("Show date"),
        help_text=_("Check to include the date in the PDF"),
    )
    image = ImageField(
        verbose_name=_("Title image"),
        help_text=_("(Optional) title image for the PDF"),
        null=True,
        blank=True,
        upload_to="uploads/",
    )
    margin = FloatField(
        verbose_name=_("Title image margins"),
        help_text=_("Margins for title image, might be needed for some printers"),
        default=0,
    )
    link = CharField(
        max_length=300,
        blank=True,
        help_text=_("(Optional) URL to include in the PDF"),
        verbose_name=_("Link"),
    )

    @property
    def link_url(self) -> str:
        """The link as a URL: https:// is put in front of a link that names no scheme."""
        link = self.link.strip()
        if link and not LINK_SCHEME_RE.match(link):
            return f"https://{link}"
        return link

    @property
    def latest_file(self) -> PDFFile:
        """Returns latest generated file for this template."""
        return self.pdffile_set.first()

    @property
    def latest_generated_file(self) -> PDFFile:
        """Returns the newest file of this template that was generated successfully, None without one."""
        return self.pdffile_set.filter(status=Status.DONE).exclude(file="").exclude(file=None).first()

    def has_scheduled_file(self) -> bool:
        """True, if the latest file created from this template is scheduled to be generated."""
        file = self.latest_file
        return bool(file and not file.finished)

    @abstractmethod
    def get_songs(self) -> Iterable[tuple[int, Song]]:
        """Returns iterable of Song objects and their song number, that should be included in the PDF."""

    def get_sections(self) -> list[Section]:
        """Returns the songs of the PDF grouped into sections in print order, one untitled section by default."""
        return [Section(None, sorted(self.get_songs(), key=lambda numbered: numbered[0]))]

    def copy_options(self, options: PDFTemplate):
        """Copy all options from another PDFOptions object."""
        self.filename = options.filename
        self.locale = options.locale
        self.title = options.title
        self.show_date = options.show_date
        self.image = options.image
        self.margin = options.margin
        self.link = options.link

    class Meta:
        abstract = False


post_delete.connect(file_cleanup, sender=PDFTemplate, dispatch_uid="pdftemplate.file_cleanup")
