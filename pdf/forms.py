"""Forms for PDF application"""
from django.core.exceptions import ValidationError
from django.forms import ModelForm, CharField, BaseFormSet, HiddenInput
from django.utils.translation import gettext_lazy as _

from pdf.models.request import PDFRequest, PDFSong


class RequestForm(ModelForm):
    """Slimmed down model form for PDFRequest"""

    class Meta:
        model = PDFRequest
        fields = ["title", "filename", "locale", "show_date", "image", "margin"]


class PDFSongForm(ModelForm):
    """Slimmed down model form for PDFSong"""

    name = CharField(disabled=True, required=False)

    class Meta:
        model = PDFSong
        fields = ["song_number", "song"]
        widgets = {"song": HiddenInput()}


class BasePDFSongFormset(BaseFormSet):
    """FormSet for PDFSongForm that checks if song_numbers are unique"""

    def clean(self):
        if any(self.errors):
            return
        numbers = set()
        for form in self.forms:
            number = form.instance.song_number
            if number in numbers:
                raise ValidationError(_("Each song has to have distinct song number"))
            numbers.add(number)
