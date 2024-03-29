# Generated by Django 5.0 on 2024-01-12 14:46

import tenants.models
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("tenants", "0002_tenant_all_songs_category"),
    ]

    operations = [
        migrations.AddField(
            model_name="tenant",
            name="icon",
            field=models.ImageField(
                blank=True,
                help_text="Optional Site Icon, needs to be a PNG",
                null=True,
                upload_to="uploads/",
                validators=[tenants.models.only_png],
                verbose_name="Site Icon",
            ),
        ),
    ]
