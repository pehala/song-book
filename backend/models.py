"""Models for backend app"""
from django.conf import settings

from django.db.models import Model, CharField, URLField, DateField, PositiveSmallIntegerField
from django.utils.translation import gettext_lazy as _
from markdownx.models import MarkdownxField


class Song(Model):
    """Song model"""
    name = CharField(verbose_name=_('Song Name'), max_length=100)
    date = DateField(auto_now_add=True, editable=False)
    capo = PositiveSmallIntegerField(verbose_name="Capo", default=0)
    author = CharField(verbose_name=_('Author'), max_length=100, null=True, blank=True)
    link = URLField(verbose_name=_("Youtube Link"), null=True, blank=True)
    locale = CharField(choices=settings.LANGUAGES, verbose_name=_('Language'), max_length=5, default="Czech")
    text = MarkdownxField(verbose_name=_('Lyrics'))

    class Meta:
        verbose_name = _('Song')
        verbose_name_plural = _('Songs')
