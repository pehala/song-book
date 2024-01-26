"""Storages for the PDF application"""

from pathlib import Path

from django.core.files.storage import FileSystemStorage


class DateOverwriteStorage(FileSystemStorage):
    """
    File storage system that saves files into folders based on current date
    and overwrites already existing files
    """

    def get_available_name(self, name, max_length=None):
        path = Path(name)
        self.delete(path)
        return path
