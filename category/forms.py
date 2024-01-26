"""Forms for category app"""

from django.forms import ModelForm, IntegerField, Form, HiddenInput, ModelChoiceField, CharField
from django.utils.translation import gettext_lazy as _

from category.models import Category
from tenants.models import Tenant


class CategoryForm(ModelForm):
    """Category form"""

    class Meta:
        model = Category
        exclude = ["tenant"]  # pylint: disable=modelform-uses-exclude


class NameForm(Form):
    """Form to show categories name"""

    pk = IntegerField(widget=HiddenInput())
    name = CharField(disabled=True, required=False)


class ChooseTenantForm(Form):
    """Form to choose Tenant"""

    tenant = ModelChoiceField(queryset=Tenant.objects.all(), label=_("Tenant"))
