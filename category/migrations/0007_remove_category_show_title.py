# Generated by Django 4.0.7 on 2022-09-26 14:45

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('category', '0006_category_link'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='category',
            name='show_title',
        ),
    ]