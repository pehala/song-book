"""Analytics views"""

import logging
from datetime import timedelta

from django.db import DatabaseError, IntegrityError, transaction
from django.db.models import F, Sum
from django.http import HttpRequest, HttpResponseBadRequest, JsonResponse

# Create your views here.
from django.urls import reverse
from django.utils.timezone import now
from django.views import View
from django.views.generic import TemplateView

from analytics.models import DayStatistic
from backend.mixins import LocalAdminRequired

logger = logging.getLogger(__name__)

ALL_SONGS_KEY = "all"


def add_hit(request, key):
    """Adds one hit to today's counter of the key, creating the counter on the first hit of the day"""
    today = DayStatistic.objects.filter(tenant=request.tenant, key=key, date=now().date())
    if today.update(hits=F("hits") + 1):
        return
    try:
        with transaction.atomic():
            DayStatistic.objects.create(tenant=request.tenant, key=key, hits=1)
    except IntegrityError:
        today.update(hits=F("hits") + 1)


def analytics(request, key):
    """Adds hit; a failing database must not break the request being counted"""
    try:
        add_hit(request, key)
    except DatabaseError:
        logger.exception("Could not count a hit for %s", key)


class AnalyticsShowView(LocalAdminRequired, TemplateView):
    """Shows analytics graphs; the browser draws them from `AnalyticsRestView`"""

    template_name = "analytics/show.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page"] = {"data": reverse("analytics:data")}
        return ctx


DEFAULT_DAYS = 7
MAX_DAYS = 3660


class AnalyticsRestView(LocalAdminRequired, View):
    """
    Returns the hits of the last `days` days, today included, for one `key` or summed over all of them
    when it is empty, one value per day, along with every key the tenant has statistics for
    """

    def get(self, request: HttpRequest, *args, **kwargs):
        """Handles GET requests"""
        try:
            days = int(request.GET.get("days", DEFAULT_DAYS))
        except ValueError:
            return HttpResponseBadRequest()
        if not 1 <= days <= MAX_DAYS:
            return HttpResponseBadRequest()
        statistics = DayStatistic.objects.filter(tenant=request.tenant)
        keys = list(statistics.order_by("key").values_list("key", flat=True).distinct())
        if key := request.GET.get("key", ""):
            statistics = statistics.filter(key=key)
        end = now().date()
        dates = [end - timedelta(days=offset) for offset in reversed(range(days))]
        totals = dict(
            statistics.filter(date__range=(dates[0], end))
            .values("date")
            .annotate(total=Sum("hits"))
            .values_list("date", "total")
        )
        return JsonResponse(
            {
                "keys": keys,
                "dates": [date.isoformat() for date in dates],
                "hits": [totals.get(date, 0) for date in dates],
            }
        )
