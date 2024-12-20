# Generated by Django 5.1.4 on 2024-12-20 18:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("backend", "0012_rename_prerendered_pdf_song_prerendered_and_more"),
        ("category", "0013_category2"),
    ]

    operations = [
        migrations.AlterField(
            model_name="song",
            name="categories",
            field=models.ManyToManyField(to="category.category2", verbose_name="Categories"),
        ),
    ]