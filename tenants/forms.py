"""Tenant forms"""

from django.forms import ModelForm, CharField, Form, ModelChoiceField

from tenants.models import Tenant, Link


class TenantForm(ModelForm):
    """Specific Form for Tenants, used only in Admin"""

    index_redirect = CharField(initial="/")

    class Meta:
        model = Tenant
        fields = "__all__"


class LinkForm(ModelForm):
    """Specific Form for Link, used only in Admin"""

    class Meta:
        model = Link
        fields = "__all__"


class UserTenantForm(ModelForm):
    """Tenant Model Form with disabled hostname"""

    hostname = CharField(disabled=True)

    class Meta:
        model = Tenant
        fields = "__all__"


class ChooseTenantForm(Form):
    """Form to choose Tenant"""

    tenant = ModelChoiceField(
        queryset=Tenant.objects.all(), label=Tenant._meta.verbose_name, blank=False, empty_label=None
    )
