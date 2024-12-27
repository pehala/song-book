"""Forms for category app"""

from django.forms import ModelForm, IntegerField, Form, HiddenInput, ModelChoiceField, CharField
from django.forms.utils import ErrorList
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from category.models import Category
from chords.widgets import AppendWidget, PrependWidget
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

    def __init__(self, request, data=None, files=None, auto_id="id_%s", prefix=None, initial=None, error_class=ErrorList,
                 label_suffix=None, empty_permitted=False, instance=None, use_required_attribute=None, renderer=None):
        super().__init__(data, files, auto_id, prefix, initial, error_class, label_suffix, empty_permitted, instance,
                         use_required_attribute, renderer)
        self.fields["slug"].widget = PrependWidget(request.build_absolute_uri(reverse('category:index', args=("i",)))[:-1])


class NameForm(Form):
    """Form to show categories name"""

    pk = IntegerField(widget=HiddenInput())
    name = CharField(disabled=True, required=False)
