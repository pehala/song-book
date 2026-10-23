"""Analytics models"""

from django.db.models import CASCADE, CharField, DateField, ForeignKey, IntegerField, Model, Value
from django.utils.translation import gettext_lazy as _

from tenants.models import Tenant


class DayStatistic(Model):
    """Statistic data for given day/key combination"""

    tenant = ForeignKey(Tenant, on_delete=CASCADE)
    key = CharField(verbose_name=_("Key"), max_length=25)
    hits = IntegerField(verbose_name=_("Hits"), db_default=Value(0))
    date = DateField(auto_now_add=True, editable=False)
