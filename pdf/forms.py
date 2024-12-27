"""Forms for PDF application"""

from django.core.exceptions import ValidationError
from django.forms import (
    ModelForm,
    CharField,
    BaseFormSet,
    HiddenInput,
    Form,
    IntegerField,
    ModelMultipleChoiceField,
)
from django.utils.translation import gettext_lazy as _

from backend.models import Song
from chords.widgets import NoopWidget, AppendWidget
from pdf.models.request import PDFSong, ManualPDFTemplate, PDFFile


class ManualTemplateForm(ModelForm):
    """Form for ManualPDFTemplate"""

    class Meta:
        model = ManualPDFTemplate
        fields = ["name", "display_name", "filename", "title", "image", "public", "locale", "show_date", "link"]
        widgets = {"filename": AppendWidget(".pdf")}


class PDFFileEditForm(ModelForm):
    """Edit form for PDFFile, allows changing only the display name"""

    filename = CharField(widget=AppendWidget(".pdf"), disabled=True)

    class Meta:
        model = PDFFile
        fields = ["display_name", "public", "filename"]


class SongSelectionForm(Form):
    """Song selection form"""

    songs = ModelMultipleChoiceField(required=True, queryset=Song.objects.all(), widget=NoopWidget)

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request")
        super().__init__(*args, **kwargs)
        self.queryset = Song.objects.filter(categories__tenant=self.request.tenant).distinct()
        self.fields["songs"].queryset = self.queryset

    def get_list_field_value(self, field_name, default=None):
        """Return current value of a List field"""
        if self.is_bound:
            return self.data.getlist(self.add_prefix(field_name), default)
        return self.initial.get(field_name, default)

    def clean(self):
        data = super().clean()
        if "songs" in self.cleaned_data:
            songs = self.cleaned_data["songs"]
            if len(songs) == 0:
                raise ValidationError(_("No songs selected"), code="no_songs")
        return data


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


class FileForm(Form):
    """Form that shows Title and filename of a request being moved"""

    pk = IntegerField(widget=HiddenInput())
    title = CharField(disabled=True, required=False)
    filename = CharField(disabled=True, required=False)
