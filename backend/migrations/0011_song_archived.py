# Generated by Django 4.0.5 on 2022-08-05 17:42

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("backend", "0010_alter_song_categories"),
    ]

    operations = [
        migrations.AddField(
            model_name="song",
            name="archived",
            field=models.BooleanField(default=False, verbose_name="Archived"),
        ),
    ]
