"""Forms for backend app"""
from django.forms import ModelForm, ModelMultipleChoiceField, CheckboxSelectMultiple

from backend.models import Song
from category.models import Category


class AdminSongForm(ModelForm):
    """Song form"""

    categories = ModelMultipleChoiceField(widget=CheckboxSelectMultiple, queryset=Category.objects.all())

    class Meta:
        model = Song
        # pylint: disable=modelform-uses-exclude
        exclude = ["prerendered"]


class SongForm(AdminSongForm):
    """Song Form that has only categories from current tenant"""

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request")
        super().__init__(*args, **kwargs)
        self.fields["categories"].queryset = Category.objects.filter(tenant=self.request.tenant)
