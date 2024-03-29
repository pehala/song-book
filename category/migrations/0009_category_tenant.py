# Generated by Django 4.2.5 on 2023-09-10 06:47

from django.db import migrations, models
import django.db.models.deletion


def attach_to_tenant(apps, schema_editor):
    # We get the model from the versioned app registry;
    # if we directly import it, it'll be the wrong version
    Tenant = apps.get_model("tenants", "Tenant")
    Category = apps.get_model("category", "Category")
    db_alias = schema_editor.connection.alias

    default_tenant = Tenant.objects.using(db_alias).first()
    all_categories = Category.objects.using(db_alias).all()
    for category in all_categories:
        category.tenant = default_tenant

    Category.objects.using(db_alias).bulk_update(all_categories, ["tenant"])


class Migration(migrations.Migration):
    dependencies = [
        ("tenants", "0001_initial"),
        ("category", "0008_category_public"),
    ]

    operations = [
        migrations.AddField(
            model_name="category",
            name="tenant",
            field=models.ForeignKey(
                default=None, on_delete=django.db.models.deletion.CASCADE, to="tenants.tenant", null=True
            ),
            preserve_default=False,
        ),
        migrations.RunPython(attach_to_tenant),
        migrations.AlterField(
            model_name="category",
            name="tenant",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="tenants.tenant"),
        ),
    ]
