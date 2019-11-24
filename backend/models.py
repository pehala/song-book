from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models

# Create your models here.
from django.db.models import Model, CharField, URLField, PositiveIntegerField, DateField, PositiveSmallIntegerField
from django.utils.translation import gettext_lazy as _
from markdownx.models import MarkdownxField

# locale_validator = RegexValidator(r"([a-z]{2}|[a-z]{2}_[a-z]{2})",  _("Your language code should in format ab_cd"))


class Song(Model):
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
