"""Storages for the PDF application"""

import os
from pathlib import Path

from django.core.files.storage import FileSystemStorage
from django.db.models import FileField


class DateOverwriteStorage(FileSystemStorage):
    """
    File storage system that saves files into folders based on current date
    and overwrites already existing files
    """

    def get_available_name(self, name, max_length=None):
        path = Path(name)
        self.delete(path)
        return path


# pylint: disable=protected-access
def file_cleanup(sender, **kwargs):
    """
    File cleanup callback used to emulate the old delete
    behavior using signals. Initially django deleted linked
    files when an object containing a File/ImageField was deleted.

    Usage:
    >>> from django.db.models.signals import post_delete
    >>> post_delete.connect(file_cleanup, sender=MyModel, dispatch_uid="mymodel.file_cleanup")
    """
    for field in sender._meta.get_fields():
        if field and isinstance(field, FileField):
            inst = kwargs["instance"]
            f = getattr(inst, field.name)
            if f:
                m = inst.__class__._default_manager
                if (
                    hasattr(f, "path")
                    and os.path.exists(f.path)
                    and not m.filter(**{f"{field.name}__exact": True}).exclude(pk=inst._get_pk_val())
                ):
                    try:
                        field.storage.delete(f.path)
                    except:  # pylint: disable=bare-except
                        pass
