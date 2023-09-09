# Generated by Django 3.1.1 on 2020-09-25 19:02

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("category", "0002_auto_20200918_1217"),
    ]

    operations = [
        migrations.AlterField(
            model_name="category",
            name="generate_pdf",
            field=models.BooleanField(
                help_text="Should the PDF file be automatically generated when a song changes?",
                verbose_name="PDF generation",
            ),
        ),
    ]
