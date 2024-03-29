# Generated by Django 3.1.1 on 2020-09-25 19:46

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("pdf", "0006_auto_20200925_1902"),
    ]

    operations = [
        migrations.AlterField(
            model_name="pdfrequest",
            name="filename",
            field=models.CharField(
                help_text="Filename of the generated PDF, please do not include .pdf",
                max_length=30,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="pdfrequest",
            name="locale",
            field=models.CharField(
                choices=[("en", "English"), ("cs", "Česky")],
                help_text="Language to be used in the generated PDF",
                max_length=5,
                verbose_name="Language",
            ),
        ),
        migrations.AlterField(
            model_name="pdfrequest",
            name="name",
            field=models.CharField(
                help_text="Name to be used on the title page of the PDF",
                max_length=100,
                null=True,
            ),
        ),
    ]
