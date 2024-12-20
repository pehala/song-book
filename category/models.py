"""Models"""

from typing import Iterable, Tuple, TYPE_CHECKING

from django.db.models import CharField, SlugField, BooleanField, ForeignKey, CASCADE, Model
from django.utils.translation import gettext_lazy as _

from pdf.models import PDFTemplate
from tenants.models import Tenant

if TYPE_CHECKING:
    from backend.models import Song


class Category(PDFTemplate):
    """Song Category"""

    tenant = ForeignKey(Tenant, on_delete=CASCADE)
    name = CharField(verbose_name=_("Name"), max_length=100)
    slug = SlugField(verbose_name=_("URL pattern"), max_length=25)
    generate_pdf = BooleanField(
        verbose_name=_("PDF generation"),
        help_text=_("Should the PDF file be automatically generated when a song changes?"),
    )

    def get_songs(self) -> Iterable[Tuple[int, "Song"]]:
        return list(enumerate(self.song_set.filter(archived=False), start=1))

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Category")
        verbose_name_plural = _("Categories")
        unique_together = [["tenant", "slug"], ["tenant", "name"]]
