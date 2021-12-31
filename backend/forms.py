"""Forms for backend app"""
from django.forms import ModelForm, ModelMultipleChoiceField, CheckboxSelectMultiple, Form, FileField

from backend.models import Song
from category.models import Category


class SongForm(ModelForm):
    """Song form"""
    categories = ModelMultipleChoiceField(widget=CheckboxSelectMultiple, queryset=Category.objects.all())

    class Meta:
        model = Song
        # pylint: disable=modelform-uses-exclude
        exclude = ["prerendered_web", "prerendered_pdf"]

class UploadFileForm(Form):
    """File upload form with selection of category"""
    categories = ModelMultipleChoiceField(widget=CheckboxSelectMultiple, queryset=Category.objects.all())
    file = FileField(required=True, allow_empty_file=False)
