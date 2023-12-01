# Generated by Django 4.2.5 on 2023-12-01 11:25

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("category", "0011_alter_category_options"),
        ("backend", "0011_song_archived"),
    ]

    operations = [
        migrations.RenameField(
            model_name="song",
            old_name="prerendered_web",
            new_name="prerendered",
        ),
        migrations.RemoveField(
            model_name="song",
            name="prerendered_pdf",
        ),
        migrations.AlterField(
            model_name="song",
            name="categories",
            field=models.ManyToManyField(to="category.category", verbose_name="Categories"),
        ),
    ]
