# Generated by Django 4.0.7 on 2022-09-29 20:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pdf', '0018_pdfrequest_progress'),
    ]

    operations = [
        migrations.AddField(
            model_name='pdfrequest',
            name='public',
            field=models.BooleanField(default=True, help_text='True, if the file should be public', verbose_name='Public file'),
        ),
    ]