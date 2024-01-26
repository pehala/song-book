"""Forms for category app"""

from django.forms import ModelForm, IntegerField, Form, HiddenInput, ModelChoiceField, CharField
from django.utils.translation import gettext_lazy as _

from category.models import Category
from tenants.models import Tenant


class CategoryForm(ModelForm):
    """Category form"""

    tenant = ModelChoiceField(queryset=Tenant.objects.all(), widget=HiddenInput())

    class Meta:
        model = Category
        fields = [
            "name",
            "slug",
            "generate_pdf",
            "tenant",
            "filename",
            "public",
            "locale",
            "title",
            "show_date",
            "image",
            "margin",
            "link",
        ]


class NameForm(Form):
    """Form to show categories name"""

    pk = IntegerField(widget=HiddenInput())
    name = CharField(disabled=True, required=False)


class ChooseTenantForm(Form):
    """Form to choose Tenant"""

    tenant = ModelChoiceField(queryset=Tenant.objects.all(), label=_("Tenant"))
