"""Common classes for PDF"""

from abc import abstractmethod
from typing import Iterable, Tuple, TYPE_CHECKING

from django.conf import settings
from django.db.models import Model, BooleanField, CharField, ImageField, FloatField, TextChoices
from django.db.models.signals import post_delete
from django.utils.translation import gettext_lazy as _
from polymorphic.models import PolymorphicModel

from pdf.storage import file_cleanup
from tenants.models import Tenant

if TYPE_CHECKING:
    from backend.models import Song
    from .request import PDFFile


class Status(TextChoices):
    """Status of PDF Request"""

    QUEUED = "QU", _("Queued")
    SCHEDULED = "SC", _("Scheduled")
    IN_PROGRESS = "PR", _("In progress")
    DONE = "DO", _("Done")
    FAILED = "FA", _("Failed")


class PDFTemplate(PolymorphicModel):
    """All options for PDF Generation in a form of an abstract model"""

    display_name = CharField(
        max_length=30,
        null=True,
        blank=True,
        help_text=_("(Optional) Display name for the generated files. If empty filename will be used"),
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
        help_text=_("True, if the file should be visible in the menu"),
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
        help_text=_("Name to be used on the title page of the PDF, usually only this or Title image should be used"),
        verbose_name=_("Title"),
    )
    show_date = BooleanField(
        default=True,
        verbose_name=_("Show date"),
        help_text=_("True, if the date should be included in the PDF"),
    )
    image = ImageField(
        verbose_name=_("Title Image"),
        help_text=_("(Optional) title image for the PDF"),
        null=True,
        blank=True,
        upload_to="uploads/",
    )
    margin = FloatField(
        verbose_name=_("Title Image margins"),
        help_text=_("Margins for title image, might be needed for some printers"),
        default=0,
    )
    link = CharField(
        max_length=300,
        blank=True,
        help_text=_("(Optional) URL Link to include in the PDF"),
        verbose_name=_("Link"),
    )

    @property
    def latest_file(self) -> "PDFFile":
        """Returns latest generated file for this template"""
        return self.pdffile_set.first()

    def has_scheduled_file(self):
        """True, if the latest file created from this template is scheduled to be generated"""
        file = self.latest_file
        return file and not file.finished

    @abstractmethod
    def get_songs(self) -> Iterable[Tuple[int, "Song"]]:
        """
        Returns iterable of Song objects and their song number, that should be included in the PDF
        """

    def copy_options(self, options: "PDFTemplate"):
        """Copy all options from another PDFOptions object"""
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
