"""Forms for category app"""

from django.forms import ModelForm, IntegerField, Form, HiddenInput, ModelChoiceField, CharField
from django.utils.translation import gettext_lazy as _

from category.models import Category
from pdf.forms import PrependWidget
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
        widgets = {"filename": PrependWidget(".pdf")}


class NameForm(Form):
    """Form to show categories name"""

    pk = IntegerField(widget=HiddenInput())
    name = CharField(disabled=True, required=False)
