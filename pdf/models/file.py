"""Module containing file wrapper database objects"""

import os
from datetime import datetime

from django.conf import settings
from django.db.models import (
    Model,
    ForeignKey,
    SET_NULL,
    IntegerField,
    CASCADE,
    FileField,
    DateTimeField,
    BooleanField,
    CharField,
)
from django.utils.translation import gettext_lazy as _

from pdf.models.request import PDFRequest
from pdf.storage import DateOverwriteStorage
from tenants.models import Tenant


fs = DateOverwriteStorage()


def upload_path(instance, filename):
    """Returns upload path for this File"""
    return datetime.now().strftime(f"pdfs/{instance.tenant_id}/%y%m%d/{filename}")


class PDFFile(Model):
    """Generated PDF file, does not contain all the information for replication, only the final result"""

    tenant = ForeignKey(Tenant, on_delete=CASCADE)
    request = ForeignKey(PDFRequest, on_delete=SET_NULL, null=True)
    file = FileField(storage=fs, upload_to=upload_path)
    time_elapsed = IntegerField(null=True)
    generated = DateTimeField()
    public = BooleanField(
        default=True,
        help_text=_("True, if the file should be public"),
        verbose_name=_("Public file"),
    )
    locale = CharField(
        choices=settings.LANGUAGES,
        verbose_name=_("Language"),
        max_length=5,
        help_text=_("Language to be used in the generated PDF"),
    )

    @property
    def filename(self):
        """Returns filename of the generated file"""
        return os.path.basename(self.file.name)

    class Meta:
        verbose_name = _("PDFFile")
        verbose_name_plural = _("PDFFile")
