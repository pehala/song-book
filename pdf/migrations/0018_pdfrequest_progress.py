# Generated by Django 4.0.7 on 2022-09-28 14:39

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("pdf", "0017_remove_pdfrequest_show_title"),
    ]

    operations = [
        migrations.AddField(
            model_name="pdfrequest",
            name="progress",
            field=models.IntegerField(default=0),
        ),
    ]
