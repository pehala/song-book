"""Storages for the PDF application"""
from datetime import datetime
from pathlib import Path

from django.core.files.storage import FileSystemStorage


class DateOverwriteStorage(FileSystemStorage):
    """
    File storage system that saves files into folders based on current date
    and overwrites already existing files
    """
    def get_available_name(self, name, max_length=None):
        parts = list(Path(name).parts)
        date = datetime.now().strftime("%y%m%d")
        parts.insert(len(parts) - 1, date)
        path = Path(*parts)
        self.delete(path)
        return path
