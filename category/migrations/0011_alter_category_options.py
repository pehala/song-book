# Generated by Django 4.2.5 on 2023-12-01 11:25

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("category", "0010_alter_category_name_alter_category_slug_and_more"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="category",
            options={"verbose_name": "Category", "verbose_name_plural": "Categories"},
        ),
    ]