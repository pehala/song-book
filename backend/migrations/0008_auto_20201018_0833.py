# Generated by Django 3.1.1 on 2020-10-18 08:33

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("backend", "0007_auto_20200918_1217"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="song",
            options={
                "ordering": ["date", "id"],
                "verbose_name": "Song",
                "verbose_name_plural": "Songs",
            },
        ),
    ]
