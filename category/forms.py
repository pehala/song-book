"""Forms for backend app"""
from django.forms import ModelForm

from category.models import Category


class CategoryForm(ModelForm):
    """Song form"""

    class Meta:
        model = Category
        fields = "__all__"
