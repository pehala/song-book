# Generated by Django 5.0 on 2024-01-12 14:46

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("category", "0011_alter_category_options"),
    ]

    operations = [
        migrations.AlterField(
            model_name="category",
            name="link",
            field=models.CharField(
                blank=True, help_text="Link to include in the PDF", max_length=300, verbose_name="Link"
            ),
        ),
    ]
