# Generated by Django 5.0.6 on 2024-06-14 12:47

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("pdf", "0024_alter_pdfrequest_link"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="pdfrequest",
            name="automated_category_present",
        ),
    ]
