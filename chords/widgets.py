"""Common Widgets to be used across app."""

from django.forms import TextInput, Widget
from django.utils.safestring import mark_safe


class NoopWidget(Widget):
    """Renders completely empty widget, but still retrieves data.

    Useful for situation when you handle submit specifically.
    """

    def render(self, name, value, attrs=None, renderer=None):
        """Renders nothing."""
        return ""

    def value_from_datadict(self, data, files, name):
        """Returns the submitted values, a list when the data has several for the name."""
        try:
            getter = data.getlist
        except AttributeError:
            getter = data.get
        return getter(name)

    @property
    def is_hidden(self):
        """Hides the widget from the form layout."""
        return True


class AppendWidget(TextInput):
    """Widget that prepend boostrap-style span with data to specified base widget."""

    def __init__(self, data, *args, **kwargs):
        """Initialise widget and get base instance."""
        super().__init__(*args, **kwargs)
        self.data = data

    def render(self, name, value, attrs=None, renderer=None):
        """Render base widget and add bootstrap spans."""
        context = self.get_context(name, value, attrs)
        field = self._render(self.template_name, context, renderer)
        return mark_safe(
            f'<div class="input-group mb-3">{field}<span class="input-group-text">{self.data}</span></div>'
        )


class PrependWidget(TextInput):
    """Widget that prepend boostrap-style span with data to specified base widget."""

    def __init__(self, data, *args, **kwargs):
        """Initialise widget and get base instance."""
        super().__init__(*args, **kwargs)
        self.data = data

    def render(self, name, value, attrs=None, renderer=None):
        """Render base widget and add bootstrap spans."""
        context = self.get_context(name, value, attrs)
        field = self._render(self.template_name, context, renderer)
        return mark_safe(
            f'<div class="input-group mb-3"><span class="input-group-text">{self.data}</span>{field}</div>'
        )
