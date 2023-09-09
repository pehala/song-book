"""Models"""
from django.db.models import CharField, SlugField, BooleanField
from django.utils.translation import gettext_lazy as _

from pdf.models import PDFOptions


class Category(PDFOptions):
    """Represents set of songs"""

    name = CharField(verbose_name=_("Name"), max_length=100, unique=True)
    slug = SlugField(verbose_name=_("URL pattern"), max_length=25, unique=True)
    generate_pdf = BooleanField(
        verbose_name=_("PDF generation"),
        help_text=_("Should the PDF file be automatically generated when a song changes?"),
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Songbook"
        verbose_name_plural = "Songbooks"
