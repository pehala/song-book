"""Models for backend app"""

from django.conf import settings
from django.db.models import (
    Model,
    CharField,
    URLField,
    DateField,
    PositiveSmallIntegerField,
    ManyToManyField,
    TextField,
    BooleanField,
)
from django.utils.translation import gettext_lazy as _
from markdownx.models import MarkdownxField

from chords.markdown import RENDERER
from category.models import Category


class Song(Model):
    """Song model"""

    name = CharField(verbose_name=_("Name"), max_length=100)
    date = DateField(auto_now_add=True, editable=False)
    capo = PositiveSmallIntegerField(verbose_name=_("Capo"), default=0)
    author = CharField(verbose_name=_("Author"), max_length=100, null=True, blank=True)
    link = URLField(verbose_name=_("Youtube Link"), null=True, blank=True)
    categories = ManyToManyField(Category, verbose_name=_("Categories"))
    archived = BooleanField(verbose_name=_("Archived"), default=False)
    text = MarkdownxField(verbose_name=_("Lyrics"))
    prerendered = TextField(null=True)

    def _get_rendered_markdown(self):
        """
        Returns rendered markdown for specific type of application.
        If USE_PRERENDERED_MARKDOWN is True, it will cache the changes indefinitely.
        If USE_DYNAMIC_PRERENDER is False, it will fail if there is no cached version ready
        """
        if not settings.USE_PRERENDERED_MARKDOWN:
            return RENDERER(self.text)

        field = self.prerendered

        if field is None:
            if settings.USE_DYNAMIC_PRERENDER:
                return self.prerender()
            raise ValueError("No prerendered song found and USE_DYNAMIC_PRERENDER is set to false")
        return field

    def prerender(self, save: bool = True):
        """Generates prerendered html for specific type with a specific rendered"""
        html = RENDERER(self.text)
        self.prerendered = html

        if save:
            self.save()
        return html

    @property
    def rendered_markdown(self):
        """Returns rendered markdown for web"""
        return self._get_rendered_markdown()

    def __str__(self):
        return f"{self.name} ({self.id})"

    class Meta:
        verbose_name = _("Song")
        verbose_name_plural = _("Songs")
        ordering = ["date", "id"]

    def __hash__(self):
        values = [
            self.name,
            self.date,
            self.capo,
            self.author,
            self.link,
            self.categories,
            self.text,
        ]
        if hasattr(self, "song_number"):
            # pylint: disable=no-member
            values.append(self.song_number)
        return hash(frozenset(values))
