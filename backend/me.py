"""Describes the user to the client-side header"""

from django.contrib.messages import get_messages
from django.middleware.csrf import get_token

from backend.auth import is_localadmin


def me_payload(request, with_messages=True):
    """
    Who is signed in and what they may do; also makes sure the CSRF cookie exists for the header's POSTs.

    The pending messages are drained into the payload unless the page shows them itself.
    """
    get_token(request)
    user = request.user
    return {
        "auth": user.is_authenticated,
        "username": user.get_username() if user.is_authenticated else None,
        "localadmin": is_localadmin(request),
        "superuser": user.is_superuser,
        "messages": [{"level": message.level_tag, "text": str(message)} for message in get_messages(request)]
        if with_messages
        else [],
    }
