"""Forms for backend app."""

from django.db.models import Q
from django.forms import CheckboxSelectMultiple, ModelForm, ModelMultipleChoiceField
from django.forms.widgets import Script
from markdownx.widgets import MarkdownxWidget

from backend.models import Song
from category.models import Category
from chords.plugins import CHORD_RE
from chords.plugins.spaces import SPACES_RE

# The chords of the chord bar of the song editor: the ones most songs use, in a fixed order
EDITOR_CHORDS = ("C", "D", "E", "F", "G", "Ami", "Emi")
# The fields the template of the song editor places itself; the editor lists every other field of the form after them
EDITOR_OWN_FIELDS = ("name", "author", "capo", "text")


class SongTextWidget(MarkdownxWidget):
    """Lyrics editor of the song editor page, which brings its chord bar, tabs and splitter."""

    def get_context(self, name, value, attrs=None):
        """Adds the chords of the chord bar and marks the widget as the one of the editor page."""
        context = super().get_context(name, value, attrs)
        context["widget"]["chords"] = EDITOR_CHORDS
        context["widget"]["editor"] = True
        return context


class AdminSongForm(ModelForm):
    """Song form."""

    class Media:
        js = [Script("backend/song_pdf_pages.js", type="module")]

    categories = ModelMultipleChoiceField(widget=CheckboxSelectMultiple, queryset=Category.objects.all())

    class Meta:
        model = Song
        exclude = ["prerendered"]


class SongForm(AdminSongForm):
    """Song Form that has only categories from current tenant."""

    class Meta(AdminSongForm.Meta):
        widgets = {
            "text": SongTextWidget(
                attrs={
                    "class": "form-control font-monospace",
                    "autocapitalize": "off",
                    "autocorrect": "off",
                    "spellcheck": "false",
                    # What the editor colours as a chord and as spaces is what the server's parser takes for them
                    "data-chord-re": CHORD_RE,
                    "data-spaces-re": SPACES_RE,
                }
            )
        }

    field_order = ["name", "author", "capo", "categories"]

    class Media:
        css = {"all": ["app/song.css", "backend/vendor/prism-code-editor.css", "backend/editor.css"]}
        js = [Script("backend/editor.js", type="module")]

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request")
        super().__init__(*args, **kwargs)
        self.fields["categories"].queryset = Category.objects.filter(tenant=self.request.tenant)

    def detail_fields(self):
        """Returns the fields the editor lists under the name, the author and the capo: all but the lyrics."""
        return [field for field in self.visible_fields() if field.name not in EDITOR_OWN_FIELDS]

    def clean_categories(self):
        """Keeps the categories the song has in other tenants, which this form neither shows nor changes."""
        chosen = self.cleaned_data["categories"]
        if not self.instance.pk:
            return chosen
        kept = self.instance.categories.exclude(tenant=self.request.tenant)
        return Category.objects.filter(Q(pk__in=chosen) | Q(pk__in=kept))
