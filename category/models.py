"""Models"""
from django.conf import settings
from django.db.models import Model, CharField, SlugField, BooleanField
from django.utils.translation import gettext_lazy as _


class Category(Model):
    """Represents set of songs"""
    name = CharField(verbose_name=_('Name'), max_length=100, unique=True)
    slug = SlugField(verbose_name=_('URL pattern'), max_length=25, unique=True)
    generate_pdf = BooleanField(verbose_name=_('PDF generation'),
                                help_text=_('Should the PDF file be automatically generated when a song '
                                            'changes?'))
    locale = CharField(choices=settings.LANGUAGES, verbose_name=_('Language'), max_length=5,
                       default="Czech", help_text=_('Language for generated PDF files'))

    def __str__(self):
        return self.name
