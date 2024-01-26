"""Models"""

from django.db.models import CharField, SlugField, BooleanField, ForeignKey, CASCADE
from django.utils.translation import gettext_lazy as _

from pdf.models import PDFOptions
from tenants.models import Tenant


class Category(PDFOptions):
    """Represents set of songs"""

    tenant = ForeignKey(Tenant, on_delete=CASCADE)
    name = CharField(verbose_name=_("Name"), max_length=100)
    slug = SlugField(verbose_name=_("URL pattern"), max_length=25)
    generate_pdf = BooleanField(
        verbose_name=_("PDF generation"),
        help_text=_("Should the PDF file be automatically generated when a song changes?"),
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Category")
        verbose_name_plural = _("Categories")
        unique_together = [["tenant", "slug"], ["tenant", "name"]]
