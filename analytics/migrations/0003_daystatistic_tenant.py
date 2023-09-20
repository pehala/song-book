# Generated by Django 4.2.5 on 2023-09-10 06:47

from django.db import migrations, models
import django.db.models.deletion


def attach_to_tenant(apps, schema_editor):
    # We get the model from the versioned app registry;
    # if we directly import it, it'll be the wrong version
    Tenant = apps.get_model("tenants", "Tenant")
    DayStatistic = apps.get_model("analytics", "DayStatistic")
    db_alias = schema_editor.connection.alias

    default_tenant = Tenant.objects.using(db_alias).first()
    statistics = DayStatistic.objects.using(db_alias).all()
    for day in statistics:
        day.tenant = default_tenant

    DayStatistic.objects.using(db_alias).bulk_update(statistics, ["tenant"])


class Migration(migrations.Migration):
    dependencies = [
        ("tenants", "0001_initial"),
        ("analytics", "0002_auto_20211212_0917"),
    ]

    operations = [
        migrations.AddField(
            model_name="DayStatistic",
            name="tenant",
            field=models.ForeignKey(
                default=None, on_delete=django.db.models.deletion.CASCADE, to="tenants.tenant", null=True
            ),
            preserve_default=False,
        ),
        migrations.RunPython(attach_to_tenant),
        migrations.AlterField(
            model_name="DayStatistic",
            name="tenant",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="tenants.tenant"),
        ),
    ]
