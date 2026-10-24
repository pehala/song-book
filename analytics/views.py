"""Analytics views"""

from datetime import timedelta
from urllib.parse import urlparse

from django.db import transaction
from django.db.models import Sum
from django.http import Http404, HttpRequest, HttpResponse, HttpResponseBadRequest, HttpResponseForbidden, JsonResponse

# Create your views here.
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.timezone import now
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView

from analytics.models import DayStatistic
from backend.mixins import LocalAdminRequired


def analytics(request, key):
    """Adds hit"""
    with transaction.atomic():
        statistic, _ = DayStatistic.objects.get_or_create(key=key, date=now(), tenant=request.tenant)
        statistic.hits += 1
        statistic.save()


ALL_SONGS_KEY = "all"


def is_same_origin(request: HttpRequest) -> bool:
    """Whether the request was made by a page of this very site"""
    origin = request.headers.get("Origin")
    if origin:
        return urlparse(origin).netloc == request.get_host()
    return request.headers.get("Sec-Fetch-Site") == "same-origin"


@method_decorator(csrf_exempt, name="dispatch")
class HitView(View):
    """Counts a page view reported by the reader, which navigates without loading pages"""

    http_method_names = ["post", "options"]

    def post(self, request: HttpRequest, key: str):
        """Adds a hit for the key, which is the slug of one of the tenant's categories or `all`"""
        if not is_same_origin(request):
            return HttpResponseForbidden()
        if key != ALL_SONGS_KEY and not request.tenant.category_set.filter(slug=key).exists():
            raise Http404(key)
        analytics(request, key)
        return HttpResponse(status=204)


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
