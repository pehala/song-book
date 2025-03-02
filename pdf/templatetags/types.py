"""Template tags for transforming PDFRequest column types"""

from django import template

from pdf.models.request import Status

register = template.Library()


@register.filter(is_safe=True)
def get_status_color(status):
    """Converts status to color"""
    if status == str(Status.QUEUED) or status == str(Status.SCHEDULED):
        return "yellow"
    if status == str(Status.IN_PROGRESS):
        return "blue"
    if status == str(Status.DONE):
        return "green"
    return "red"
