# Generated by Django 5.1.4 on 2024-12-20 19:54

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("pdf", "0027_pdffile_template_delete_pdfsong"),
    ]

    operations = [
        migrations.DeleteModel(
            name="PDFRequest",
        ),
    ]