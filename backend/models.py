"""Models for backend app"""

from django.db.models import Model, CharField, URLField, DateField, PositiveSmallIntegerField, ManyToManyField
from django.utils.translation import gettext_lazy as _
from markdownx.models import MarkdownxField

from category.models import Category


class Song(Model):
    """Song model"""
    name = CharField(verbose_name=_("Name"), max_length=100)
    date = DateField(auto_now_add=True, editable=False)
    capo = PositiveSmallIntegerField(verbose_name="Capo", default=0)
    author = CharField(verbose_name=_("Author"), max_length=100, null=True, blank=True)
    link = URLField(verbose_name=_("Youtube Link"), null=True, blank=True)
    categories = ManyToManyField(Category, verbose_name=_("Categories"))
    text = MarkdownxField(verbose_name=_("Lyrics"))

    class Meta:
        verbose_name = _('Song')
        verbose_name_plural = _('Songs')
        ordering = ['date', 'id']

    def __hash__(self):
        values = [self.name, self.date, self.capo, self.author,
                  self.link, self.categories, self.text]
        if hasattr(self, "song_number"):
            # pylint: disable=no-member
            values.append(self.song_number)
        return hash(frozenset(values))
