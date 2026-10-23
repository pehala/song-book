"""Analytics views"""

from datetime import UTC, datetime, timedelta
from urllib.parse import urlparse

from django.db import transaction
from django.db.models import Sum
from django.http import Http404, HttpRequest, HttpResponse, HttpResponseBadRequest, HttpResponseForbidden, JsonResponse

# Create your views here.
from django.utils.decorators import method_decorator
from django.utils.timezone import now
from django.utils.translation import gettext_noop
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


class AnalyticsMixin(View):
    """Mixin for gathering number of hits per day analytics"""

    KEY = gettext_noop("General")

    def get_key(self):
        """Returns Key to be used in analytics"""
        return self.KEY

    def dispatch(self, request, *args, **kwargs):
        result = super().dispatch(request, *args, **kwargs)
        analytics(request, self.get_key())
        return result


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
    """Shows analytics graphs"""

    template_name = "analytics/show.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["keys"] = (
            DayStatistic.objects.filter(tenant=self.request.tenant)
            .order_by("key")
            .values_list("key", flat=True)
            .distinct()
        )
        ctx["now"] = now().date()
        ctx["week"] = (now() - timedelta(days=6)).date()
        # ctx["day"] = (now() - timedelta(days=1)).date()
        ctx["month"] = (now() - timedelta(days=30)).date()
        ctx["year"] = (now() - timedelta(days=360)).date()
        return ctx


class AnalyticsRestView(LocalAdminRequired, View):
    """Returns analytics data for given dates and key"""

    def post(self, request: HttpRequest, *args, **kwargs):
        """Handles GET requests"""
        if "start_date" not in request.POST or "key" not in request.POST:
            return HttpResponseBadRequest()
        start_date = datetime.fromtimestamp(int(request.POST["start_date"]), tz=UTC).date()
        if "end_date" in request.POST:
            end_date = datetime.fromtimestamp(int(request.POST["end_date"]), tz=UTC).date()
        else:
            end_date = now().date()
        key = request.POST["key"]
        if len(key) > 0:
            days = DayStatistic.objects.filter(
                date__gte=start_date, date__lte=end_date, key=key, tenant=self.request.tenant
            )
        else:
            days = DayStatistic.objects.filter(date__gte=start_date, date__lte=end_date, tenant=self.request.tenant)
        days = days.values("date").annotate(total=Sum("hits")).values("date", "total").order_by("date")
        return JsonResponse({entry["date"].isoformat(): entry["total"] for entry in days})
