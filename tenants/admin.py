"""Admin models for Tenants"""
from django.conf import settings
from django.contrib import admin
from django.urls import reverse_lazy, reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from category.models import Category
from tenants.forms import TenantForm
from tenants.models import Tenant


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    """Tenant Admin view"""

    list_display = ["name", "hostname_link", "display_name"]
    form = TenantForm

    @admin.display(description=_("Tenant"))
    def hostname_link(self, obj):
        """Shows link to the tenants homepage"""
        link = reverse("chords:index")
        return format_html('<a href="{}{}">{}</a>', obj.hostname, link, obj.hostname)

    def save_model(self, request, obj, form, change):
        """Overrides saving method to create default category and redirect index page to it"""
        if obj.index_redirect == "/":
            obj.index_redirect = reverse_lazy("category:index", kwargs={"slug": "default"})
        super().save_model(request, obj, form, change)
        if not Category.objects.filter(tenant=obj).exists():
            Category.objects.create(
                tenant=obj, name="Default Category", slug="default", locale=settings.LANGUAGES[0][0], generate_pdf=False
            )


admin.site.login_template = "registration/login.html"
