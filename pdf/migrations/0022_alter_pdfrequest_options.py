# Generated by Django 4.2.5 on 2023-09-18 20:18

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("pdf", "0021_pdfrequest_tenant"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="pdfrequest",
            options={"ordering": ["-update_date"], "verbose_name": "PDFRequest", "verbose_name_plural": "PDFRequests"},
        ),
    ]
