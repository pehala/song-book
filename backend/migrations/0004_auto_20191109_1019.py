# Generated by Django 2.2.7 on 2019-11-09 10:19

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("backend", "0003_auto_20191109_0912"),
    ]

    operations = [
        migrations.AlterField(
            model_name="song",
            name="locale",
            field=models.CharField(
                choices=[("en", "English"), ("cs", "Czech")],
                max_length=5,
                verbose_name="Language",
            ),
        ),
    ]
