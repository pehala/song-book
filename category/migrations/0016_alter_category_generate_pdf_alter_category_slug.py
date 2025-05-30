# Generated by Django 5.1.4 on 2024-12-27 19:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("category", "0015_rename_category2_category"),
    ]

    operations = [
        migrations.AlterField(
            model_name="category",
            name="generate_pdf",
            field=models.BooleanField(
                help_text="True, if the PDF file be automatically generated when a category or song changes?",
                verbose_name="PDF generation",
            ),
        ),
        migrations.AlterField(
            model_name="category",
            name="slug",
            field=models.SlugField(
                help_text="URL Slug, under which the category should be accessible",
                max_length=25,
                verbose_name="URL Slug",
            ),
        ),
    ]
