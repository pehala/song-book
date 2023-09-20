"""Tenant models"""
from django.contrib.auth import get_user_model
from django.db.models import Model, CharField, ManyToManyField
from django.utils.translation import gettext_lazy as _

# Create your models here.


class Tenant(Model):
    """Represents a Tenant, who has own Categories and is determined by a Host Header"""

    hostname = CharField(
        verbose_name=_("Hostname"), help_text=_("The exact hostname for this Tenant"), unique=True, max_length=64
    )
    name = CharField(verbose_name=_("Name"), help_text=_("Internal name for this Tenant"), max_length=32)
    display_name = CharField(verbose_name=_("Title"), help_text=_("Title on the Main site"), max_length=32)
    index_redirect = CharField(
        verbose_name=_("Index redirect path"),
        help_text=_("Where should new tenant redirect from index page, usually a category slug"),
        max_length=32,
    )
    admins = ManyToManyField(get_user_model())

    def __str__(self):
        return f"{self.name} ({self.id})"
