"""PDF Admin classes"""

from urllib.parse import urlencode

from django.contrib import admin
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy, reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from pdf.models.request import ManualPDFTemplate
from tenants.models import Tenant


@admin.register(ManualPDFTemplate)
class RequestAdmin(admin.ModelAdmin):
    """Request Model Admin"""

    list_display = ["id", "name", "tenant_name"]
    actions = ["move_tenant"]

    @admin.display(description=Tenant._meta.verbose_name)
    def tenant_name(self, obj):
        """Shows Tenant name"""
        link = reverse("admin:tenants_tenant_change", args=[obj.tenant.id])
        return format_html('<a href="{}">{}</a>', link, obj.tenant.name)

    @admin.action(description=_("Move Request to a different Tenant"))
    def move_tenant(self, request, queryset):
        """Move Request to a different Tenant"""
        ids = queryset.values_list("id", flat=True)
        url = f"{reverse_lazy('pdf:templates:move')}?{urlencode({'pk': list(ids)}, True)}"
        return HttpResponseRedirect(url)
