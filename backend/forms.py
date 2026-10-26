"""Forms for backend app."""

from django.db.models import Q
from django.forms import CheckboxSelectMultiple, ModelForm, ModelMultipleChoiceField
from django.forms.widgets import Script

from backend.models import Song
from category.models import Category


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

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request")
        super().__init__(*args, **kwargs)
        self.fields["categories"].queryset = Category.objects.filter(tenant=self.request.tenant)

    def clean_categories(self):
        """Keeps the categories the song has in other tenants, which this form neither shows nor changes."""
        chosen = self.cleaned_data["categories"]
        if not self.instance.pk:
            return chosen
        kept = self.instance.categories.exclude(tenant=self.request.tenant)
        return Category.objects.filter(Q(pk__in=chosen) | Q(pk__in=kept))
