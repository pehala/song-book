"""Tenant forms"""

from django.forms import ModelForm, CharField

from tenants.models import Tenant


class TenantForm(ModelForm):
    """Specific Form for Tenants, used only in Admin"""

    index_redirect = CharField(initial="/")

    class Meta:
        model = Tenant
        fields = "__all__"


class UserTenantForm(ModelForm):
    """Tenant Model Form with disabled hostname"""

    hostname = CharField(disabled=True)

    class Meta:
        model = Tenant
        fields = "__all__"
