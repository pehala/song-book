"""Forms for PDF application."""

from django.core.exceptions import ValidationError
from django.db.models import TextChoices
from django.forms import (
    BaseFormSet,
    CharField,
    ChoiceField,
    Form,
    HiddenInput,
    IntegerField,
    ModelForm,
    ModelMultipleChoiceField,
)
from django.utils.translation import gettext_lazy as _

from backend.models import Song
from chords.widgets import AppendWidget, NoopWidget
from pdf.models import group_sections
from pdf.models.request import ManualPDFTemplate, PDFFile, PDFSong


class SectionStart(TextChoices):
    """How the sections of a file template start off."""

    NONE = "", _("No sections")
    CATEGORY = "category", _("By category")


class ManualTemplateForm(ModelForm):
    """Form for ManualPDFTemplate."""

    class Meta:
        model = ManualPDFTemplate
        fields = ["name", "display_name", "filename", "title", "image", "public", "locale", "show_date", "link"]
        widgets = {"filename": AppendWidget(".pdf")}


class PDFFileEditForm(ModelForm):
    """Edit form for PDFFile, allows changing only the display name."""

    filename = CharField(widget=AppendWidget(".pdf"), disabled=True)

    class Meta:
        model = PDFFile
        fields = ["display_name", "public", "filename"]


class SongSelectionForm(Form):
    """Song selection form."""

    # Not required on the field itself, so that clean() can report the error in its own words
    songs = ModelMultipleChoiceField(required=False, queryset=Song.objects.all(), widget=NoopWidget)
    sections = ChoiceField(
        required=False,
        choices=SectionStart.choices,
        label=_("Sections"),
        help_text=_("Divide the songs into sections, which can be changed when ordering them"),
    )

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request")
        super().__init__(*args, **kwargs)
        self.queryset = Song.objects.filter(categories__tenant=self.request.tenant).distinct()
        self.fields["songs"].queryset = self.queryset

    def get_list_field_value(self, field_name, default=None):
        """Return current value of a List field."""
        if self.is_bound:
            return self.data.getlist(self.add_prefix(field_name), default)
        return self.initial.get(field_name, default)

    def clean(self):
        """Requires at least one selected song."""
        data = super().clean()
        if "songs" in self.cleaned_data:
            songs = self.cleaned_data["songs"]
            if len(songs) == 0:
                raise ValidationError(_("No songs selected"), code="no_songs")
        return data


class PDFSongForm(ModelForm):
    """Slimmed down model form for PDFSong."""

    name = CharField(disabled=True, required=False)

    class Meta:
        model = PDFSong
        fields = ["song_number", "song", "section"]
        widgets = {"song": HiddenInput(), "section": HiddenInput()}

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request")
        super().__init__(*args, **kwargs)
        self.fields["song"].queryset = Song.objects.filter(categories__tenant=self.request.tenant).distinct()


class BasePDFSongFormset(BaseFormSet):
    """FormSet for PDFSongForm that checks if song_numbers are unique and the sections are in one piece."""

    def clean(self):
        """Requires a song number on every song and no number twice."""
        if any(self.errors):
            return
        numbers = set()
        for form in self.forms:
            number = form.instance.song_number
            if number in numbers:
                raise ValidationError(_("Each song must have a distinct number"))
            numbers.add(number)
        sections = group_sections(
            (form.cleaned_data["song_number"], form.cleaned_data["song"], form.cleaned_data["section"])
            for form in sorted(self.forms, key=lambda form: form.cleaned_data["song_number"])
        )
        titles = [str(section.title) for section in sections if section.title]
        split = sorted({title for title in titles if titles.count(title) > 1})
        if split:
            raise ValidationError(
                _("Each section has to be in one piece, these are split up: %(titles)s"),
                code="split_sections",
                params={"titles": ", ".join(split)},
            )


class FileForm(Form):
    """Form that shows Title and filename of a request being moved."""

    pk = IntegerField(widget=HiddenInput())
    title = CharField(disabled=True, required=False)
    filename = CharField(disabled=True, required=False)
