# Generated by Django 5.1.4 on 2024-12-25 19:56

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("tenants", "0006_alter_tenant_links"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="tenant",
            options={"verbose_name": "Tenant", "verbose_name_plural": "Tenants"},
        ),
    ]
