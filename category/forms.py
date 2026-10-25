"""Forms for category app"""

from django.forms import CharField, Form, HiddenInput, IntegerField, ModelChoiceField, ModelForm
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from category.models import Category
from chords.widgets import AppendWidget, PrependWidget
from pdf.models.request import AllSongsTemplate
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


class AllSongsForm(ModelForm):
    """All songs PDF form"""

    name = CharField(label=_("Name"), disabled=True, required=False)
    field_order = ["name"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["name"].initial = self.instance.name

    class Meta:
        model = AllSongsTemplate
        fields = [
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


class NameForm(Form):
    """Form to show categories name"""

    pk = IntegerField(widget=HiddenInput())
    name = CharField(disabled=True, required=False)
