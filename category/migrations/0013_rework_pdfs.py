# Generated by Django 5.0 on 2024-01-20 16:55

import django.db.models.deletion
from django.db import migrations, models

from pdf.models.request import RequestType, Status


def category_request(apps, schema_editor):
    # We get the model from the versioned app registry;
    # if we directly import it, it'll be the wrong version
    PDFRequest = apps.get_model("pdf", "PDFRequest")
    Category = apps.get_model("category", "Category")
    db_alias = schema_editor.connection.alias

    for category in Category.objects.using(db_alias).all():
        request = PDFRequest.objects.using(db_alias).create(
            filename=category.filename,
            locale=category.locale,
            title=category.title,
            show_date=category.show_date,
            image=category.image,
            margin=category.margin,
            link=category.link,
            type=RequestType.EVENT,
            status=Status.DONE,
        )

        category.request = request
        category.save()


class Migration(migrations.Migration):
    dependencies = [
        ("category", "0012_alter_category_link"),
        ("pdf", "0025_temp_category"),
    ]

    operations = [
        migrations.AddField(
            model_name="category",
            name="request",
            field=models.OneToOneField(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                serialize=False,
                to="pdf.pdfrequest",
            ),
            preserve_default=False,
        ),
        migrations.RunPython(category_request),
        migrations.AlterField(
            model_name="category",
            name="request",
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to="pdf.pdfrequest"),
        ),
        migrations.RemoveField(
            model_name="category",
            name="filename",
        ),
        migrations.RemoveField(
            model_name="category",
            name="image",
        ),
        migrations.RemoveField(
            model_name="category",
            name="link",
        ),
        migrations.RemoveField(
            model_name="category",
            name="locale",
        ),
        migrations.RemoveField(
            model_name="category",
            name="margin",
        ),
        migrations.RemoveField(
            model_name="category",
            name="public",
        ),
        migrations.RemoveField(
            model_name="category",
            name="show_date",
        ),
        migrations.RemoveField(
            model_name="category",
            name="title",
        ),
    ]
