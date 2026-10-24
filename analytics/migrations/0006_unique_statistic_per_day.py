from django.db import migrations, models
from django.db.models import Count, Min, Sum


def merge_duplicates(apps, schema_editor):
    """Folds rows sharing tenant, key and date into the oldest one"""
    DayStatistic = apps.get_model("analytics", "DayStatistic")
    groups = (
        DayStatistic.objects.values("tenant", "key", "date")
        .annotate(rows=Count("id"), total=Sum("hits"), first=Min("id"))
        .filter(rows__gt=1)
    )
    for group in groups:
        rows = DayStatistic.objects.filter(tenant=group["tenant"], key=group["key"], date=group["date"])
        rows.filter(id=group["first"]).update(hits=group["total"])
        rows.exclude(id=group["first"]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("analytics", "0005_alter_daystatistic_hits"),
    ]

    operations = [
        migrations.RunPython(merge_duplicates, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="daystatistic",
            constraint=models.UniqueConstraint(fields=("tenant", "key", "date"), name="unique_statistic_per_day"),
        ),
    ]
