# Generated by Django 2.2.7 on 2019-11-09 08:02

import django.core.validators
from django.db import migrations, models
import markdownx.models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Song",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=100, verbose_name="Song Name")),
                (
                    "song_number",
                    models.PositiveIntegerField(unique=True, verbose_name="Song Number"),
                ),
                (
                    "author",
                    models.CharField(max_length=100, null=True, verbose_name="Author"),
                ),
                ("link", models.URLField(null=True, verbose_name="Youtube Link")),
                (
                    "locale",
                    models.CharField(
                        max_length=5,
                        validators=[
                            django.core.validators.RegexValidator(
                                "[a-z]{2}|[a-z]{2}_[a-z]{2})",
                                "Your language code should in format ab_cd",
                            )
                        ],
                        verbose_name="Language",
                    ),
                ),
                ("text", markdownx.models.MarkdownxField(verbose_name="Lyrics")),
            ],
            options={
                "verbose_name": "Song",
                "verbose_name_plural": "Songs",
            },
        ),
    ]
