"""Forms for backend app"""
from django.forms import ModelForm, ModelMultipleChoiceField, CheckboxSelectMultiple

from backend.models import Song
from category.models import Category


class SongForm(ModelForm):
    """Song form"""

    categories = ModelMultipleChoiceField(widget=CheckboxSelectMultiple, queryset=Category.objects.all())

    class Meta:
        model = Song
        # pylint: disable=modelform-uses-exclude
        exclude = ["prerendered_web", "prerendered_pdf"]
