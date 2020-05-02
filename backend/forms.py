"""Forms for backend app"""
from django.forms import ModelForm

from backend.models import Song


class SongForm(ModelForm):
    """Song form"""
    class Meta:
        model = Song
        fields = '__all__'
