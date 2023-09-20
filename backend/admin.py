"""Backend Admin pages"""
from django.contrib import admin

from backend.forms import AdminSongForm
from backend.models import Song


@admin.register(Song)
class SongAdmin(admin.ModelAdmin):
    """Song Admin config"""

    form = AdminSongForm
    list_display = ["name", "get_categories"]

    @admin.display(description="Categories")
    def get_categories(self, obj):
        """Displays all categorties in a string"""
        return "\n".join([p.name for p in obj.categories.all()])

    get_categories.admin_order_field = "categories__name"
