"""Common classes for PDF"""
from django.conf import settings
from django.db.models import Model, BooleanField, CharField, ImageField, FloatField
from django.utils.translation import gettext_lazy as _


class PDFOptions(Model):
    """All options for PDF Generation in a form of a abstract model"""
    filename = CharField(max_length=30,
                         blank=True,
                         help_text=_("Filename of the generated PDF, please do not include .pdf"),
                         verbose_name=_("File name"))
    public = BooleanField(default=True,
                          help_text=_("True, if the file should be public"),
                          verbose_name=_("Public file"))
    locale = CharField(choices=settings.LANGUAGES, verbose_name=_('Language'), max_length=5,
                       help_text=_("Language to be used in the generated PDF")
                       )
    title = CharField(max_length=100,
                      blank=True,
                      help_text=_("Name to be used on the title page of the PDF"),
                      verbose_name=_("Title"))
    show_date = BooleanField(default=True, verbose_name=_("Show date"),
                             help_text=_("True, if the date should be included in the final PDF"))
    image = ImageField(verbose_name=_("Title Image"),
                       help_text=_("Optional title image of the songbook"),
                       null=True,
                       blank=True,
                       upload_to='uploads/')
    margin = FloatField(verbose_name=_("Title Image margins"),
                        help_text=_("Margins for title image, might be needed for some printers"),
                        default=0)
    link = CharField(max_length=300,
                     blank=True,
                     help_text=_("Link to include in the PDF"),
                     verbose_name=_("Link"),
                     default=settings.PDF_INCLUDE_LINK)

    def copy_options(self, options: "PDFOptions"):
        """Copy all options from another PDFOptions object"""
        self.filename = options.filename
        self.locale = options.locale
        self.title = options.title
        self.show_date = options.show_date
        self.image = options.image
        self.margin = options.margin
        self.link = options.link

    class Meta:
        abstract = True
