# Generated by Django 5.1.4 on 2024-12-20 19:16

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pdf", "0026_pdftemplate_pdffile_alter_pdfrequest_options_and_more"),
    ]

    operations = [
        migrations.DeleteModel(
            name="PDFSong",
        ),
    ]
