"""Analytics views"""

from datetime import datetime, timedelta

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Sum
from django.http import HttpResponseBadRequest, HttpRequest, JsonResponse

# Create your views here.
from django.utils.decorators import method_decorator
from django.utils.timezone import now
from django.utils.translation import gettext_noop
from django.views import View
from django.views.generic import TemplateView

from analytics.models import DayStatistic


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


@method_decorator(login_required, name="dispatch")
class AnalyticsShowView(TemplateView):
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
        ctx["now"] = datetime.now().date()
        ctx["week"] = (datetime.now() - timedelta(days=6)).date()
        # ctx["day"] = (datetime.now() - timedelta(days=1)).date()
        ctx["month"] = (datetime.now() - timedelta(days=30)).date()
        ctx["year"] = (datetime.now() - timedelta(days=360)).date()
        return ctx


@method_decorator(login_required, name="dispatch")
class AnalyticsRestView(View):
    """Returns analytics data for given dates and key"""

    def get(self, request: HttpRequest, *args, **kwargs):
        """Handles GET requests"""
        if "start_date" not in request.GET or "key" not in request.GET:
            return HttpResponseBadRequest()
        start_date = datetime.fromtimestamp(int(request.GET["start_date"])).date()
        if "end_date" in request.GET:
            end_date = datetime.fromtimestamp(int(request.GET["end_date"])).date()
        else:
            end_date = datetime.now().date()
        key = request.GET["key"]
        if len(key) > 0:
            days = DayStatistic.objects.filter(
                date__gte=start_date, date__lte=end_date, key=key, tenant=self.request.tenant
            )
        else:
            days = DayStatistic.objects.filter(date__gte=start_date, date__lte=end_date, tenant=self.request.tenant)
        days = days.values("date").annotate(total=Sum("hits")).values("date", "total").order_by("date")
        return JsonResponse({entry["date"].isoformat(): entry["total"] for entry in days})
