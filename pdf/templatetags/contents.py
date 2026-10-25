"""Template filters of the table of contents of a songbook PDF."""

from django import template

register = template.Library()


@register.filter
def without_last_word(title):
    """The title up to its last word, trailing space included; empty for a one-word title."""
    head, space, _last = title.rpartition(" ")
    return head + space


@register.filter
def last_word(title):
    """The last word of a title, the one the leader dots and the page number stay with."""
    return title.rpartition(" ")[2]
