from django.conf import settings
from django.forms import ModelForm

from backend.fields import ListTextWidget
from backend.models import Song


class SongForm(ModelForm):

    class Meta:
        model = Song
        fields = '__all__'
