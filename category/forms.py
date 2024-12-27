"""Forms for category app"""

from django.forms import ModelForm, IntegerField, Form, HiddenInput, ModelChoiceField, CharField
from django.urls import reverse

from category.models import Category
from chords.widgets import AppendWidget, PrependWidget
from tenants.models import Tenant


class CategoryForm(ModelForm):
    """Category form"""

    tenant = ModelChoiceField(queryset=Tenant.objects.all(), widget=HiddenInput())

    class Meta:
        model = Category
        fields = [
            "name",
            "slug",
            "tenant",
            "generate_pdf",
            "title",
            "display_name",
            "filename",
            "public",
            "locale",
            "show_date",
            "image",
            "link",
        ]
        widgets = {"filename": AppendWidget(".pdf")}

    def __init__(self, request, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["slug"].widget = PrependWidget(
            request.build_absolute_uri(reverse("category:index", args=("i",)))[:-1]
        )


class NameForm(Form):
    """Form to show categories name"""

    pk = IntegerField(widget=HiddenInput())
    name = CharField(disabled=True, required=False)
