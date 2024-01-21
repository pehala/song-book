# Generated by Django 5.0 on 2024-01-20 16:55

import django.db.models.deletion
import pdf.models.file
import pdf.storage
from django.db import migrations, models


def request_to_file(apps, schema_editor):
    # We get the model from the versioned app registry;
    # if we directly import it, it'll be the wrong version
    PDFRequest = apps.get_model("pdf", "PDFRequest")
    Category = apps.get_model("category", "Category")
    PDFFile = apps.get_model("pdf", "PDFFile")
    db_alias = schema_editor.connection.alias

    new_requests = {}
    for filename in PDFRequest.objects.using(db_alias).filter(type="MA").values_list("filename", flat=True):
        new_requests[filename] = (
            PDFRequest.objects.using(db_alias).filter(filename=filename).order_by("-update_date").first()
        )

    for request in PDFRequest.objects.using(db_alias).exclude(file=""):
        category = None
        if request.categoryID:
            category = Category.objects.using(db_alias).get(id=request.categoryID)
            new_request = category.request
        else:
            new_request = new_requests[request.filename]

        tenant = request.tenant
        if category:
            tenant = category.tenant

        PDFFile.objects.using(db_alias).create(
            tenant=tenant,
            request=new_request,
            file=request.file,
            public=request.public,
            locale=request.locale,
            time_elapsed=request.time_elapsed,
            generated=request.update_date,
        )

    ids = list(Category.objects.using(db_alias).values_list("request__id", flat=True))
    ids.extend(request.id for request in new_requests.values())

    PDFRequest.objects.using(db_alias).exclude(id__in=ids).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("pdf", "0025_temp_category"),
        ("category", "0013_rework_pdfs"),
        ("tenants", "0004_alter_tenant_icon"),
    ]

    operations = [
        migrations.AddField(
            model_name="pdfrequest",
            name="last_generated",
            field=models.DateTimeField(null=True),
        ),
        migrations.CreateModel(
            name="PDFFile",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "file",
                    models.FileField(storage=pdf.storage.DateOverwriteStorage(), upload_to=pdf.models.file.upload_path),
                ),
                ("time_elapsed", models.IntegerField(null=True)),
                ("generated", models.DateTimeField()),
                (
                    "tenant",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="tenants.tenant"),
                ),
                (
                    "request",
                    models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to="pdf.pdfrequest"),
                ),
                (
                    "public",
                    models.BooleanField(
                        default=True, help_text="True, if the file should be public", verbose_name="Public file"
                    ),
                ),
                (
                    "locale",
                    models.CharField(
                        choices=[("en", "English"), ("cs", "Česky")],
                        default="test",
                        help_text="Language to be used in the generated PDF",
                        max_length=5,
                        verbose_name="Language",
                    ),
                ),
            ],
            options={
                "verbose_name": "PDF",
                "verbose_name_plural": "PDF",
            },
        ),
        migrations.RunPython(request_to_file),
        migrations.RemoveField(
            model_name="pdfrequest",
            name="file",
        ),
        migrations.RemoveField(
            model_name="pdfrequest",
            name="time_elapsed",
        ),
        migrations.RemoveField(
            model_name="pdfrequest",
            name="update_date",
        ),
        migrations.RemoveField(
            model_name="pdfrequest",
            name="categoryID",
        ),
    ]