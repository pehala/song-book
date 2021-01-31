"""Models for backend app"""
from django.conf import settings
from django.db.models import Model, CharField, URLField, DateField, PositiveSmallIntegerField, ManyToManyField, \
    TextField, ForeignKey, CASCADE, TextChoices, IntegerChoices, IntegerField
from django.utils.translation import gettext_lazy as _
from markdownx.models import MarkdownxField

from backend.templatetags.markdown import template_markdown, pdf_markdown
from category.models import Category


class MarkdownTypes(IntegerChoices):
    WEB = 0
    PDF = 1


class Song(Model):
    """Song model"""
    name = CharField(verbose_name=_("Name"), max_length=100)
    date = DateField(auto_now_add=True, editable=False)
    capo = PositiveSmallIntegerField(verbose_name="Capo", default=0)
    author = CharField(verbose_name=_("Author"), max_length=100, null=True, blank=True)
    link = URLField(verbose_name=_("Youtube Link"), null=True, blank=True)
    categories = ManyToManyField(Category, verbose_name=_("Categories"))
    text = MarkdownxField(verbose_name=_("Lyrics"))
    prerendered_web = TextField(null=True)
    prerendered_pdf = TextField(null=True)

    def _get_rendered_markdown(self, markdown, markdown_type: MarkdownTypes):
        if not settings.USE_PRERENDERED_MARKDOWN:
            return markdown.convert(self.text)

        if markdown_type == MarkdownTypes.WEB:
            field = self.prerendered_web
        else:
            field = self.prerendered_pdf

        if field is None:
            if settings.USE_DYNAMIC_PRERENDER:
                return self._prerender(markdown, markdown_type)
            raise ValueError("No prerendered song found and USE_DYNAMIC_PRERENDER is set to false")
        return field

    def _prerender(self, markdown, markdown_type: MarkdownTypes):
        html = markdown.convert(self.text)
        if markdown_type == MarkdownTypes.WEB:
            self.prerendered_web = html
        else:
            self.prerendered_pdf = html
        self.save()
        return html

    def prerender_all(self):
        self._prerender(template_markdown, MarkdownTypes.WEB)
        self._prerender(pdf_markdown, MarkdownTypes.PDF)

    def get_web_markdown(self):
        return self._get_rendered_markdown(template_markdown, MarkdownTypes.WEB)

    def get_pdf_markdown(self):
        return self._get_rendered_markdown(pdf_markdown, MarkdownTypes.PDF)

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

#
# class PrerenderedMarkdown(Model):
#     song = ForeignKey(Song, on_delete=CASCADE)
#     type = IntegerField(choices=MarkdownTypes.choices)
#     html = TextField()
#
#     class Meta:
#         unique_together = ("song", "type")
