"""Category admin classes"""

from django.contrib import admin
from django.http import HttpResponseRedirect
from django.urls import reverse, reverse_lazy
from django.utils.html import format_html
from django.utils.http import urlencode
from django.utils.translation import gettext_lazy as _

from category.models import Category


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """Category Admin Model"""

    list_display = ["name", "tenant_name"]
    # list_display_links = ["tenant_name"]
    actions = ["move_tenant"]

    @admin.display(description=_("Tenant"))
    def tenant_name(self, obj):
        """Shows Tenant name"""
        link = reverse("admin:tenants_tenant_change", args=[obj.tenant.id])
        return format_html('<a href="{}">{}</a>', link, obj.tenant.name)

    @admin.action(description=_("Move Category to a different Tenant"))
    def move_tenant(self, request, queryset):
        """Moves Categories to a different Tenant"""
        ids = queryset.values_list("id", flat=True)
        url = f"{reverse_lazy('category:move')}?{urlencode({'pk': list(ids)}, True)}"
        return HttpResponseRedirect(url)

    tenant_name.admin_order_field = "tenant__id"
