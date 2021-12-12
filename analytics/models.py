"""Analytics models"""
from django.db.models import Model, CharField, IntegerField, DateField
from django.utils.translation import gettext_lazy as _


class DayStatistic(Model):
    """Statistic data for given day/key combination"""
    key = CharField(verbose_name=_("Key"), max_length=25)
    hits = IntegerField(verbose_name=_("Hits"), default=0)
    date = DateField(auto_now_add=True, editable=False)
