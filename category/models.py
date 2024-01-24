"""Models"""

from django.db.models import CharField, SlugField, BooleanField, ForeignKey, CASCADE, Model, OneToOneField
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _

from pdf.models import PDFRequest, RequestType
from tenants.models import Tenant


class Category(Model):
    """Represents set of songs"""

    tenant = ForeignKey(Tenant, on_delete=CASCADE)
    name = CharField(verbose_name=_("Name"), max_length=100)
    slug = SlugField(verbose_name=_("URL pattern"), max_length=25)
    request = OneToOneField(
        PDFRequest,
        on_delete=CASCADE,
        primary_key=False,
    )
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


# pylint: disable=unused-argument
@receiver(post_save, sender=Category)
def create_pdf_request(signal, instance, created, **kwargs):
    """Generates a new PDFRequest for new category if not present"""
    if created:
        if not hasattr(instance, "request"):
            request = PDFRequest.objects.create(type=RequestType.EVENT)
            created.request = request
            created.save()
