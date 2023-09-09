# Generated by Django 3.0.7 on 2020-09-18 12:17

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("backend", "0006_category_20200809_0529"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="song",
            options={
                "ordering": ["date"],
                "verbose_name": "Song",
                "verbose_name_plural": "Songs",
            },
        ),
        migrations.AlterField(
            model_name="song",
            name="name",
            field=models.CharField(max_length=100, verbose_name="Name"),
        ),
    ]
