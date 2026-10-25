"""Context of the pages that draw the shared header."""

from backend.me import me_payload
from tenants.bootstrap import bootstrap_payload


def header(request):
    """The header's bootstrap and user; templates call them, so only the pages that print them pay for them."""
    return {
        "boot": lambda: bootstrap_payload(request.tenant),
        "me": lambda: me_payload(request, with_messages=False),
    }
