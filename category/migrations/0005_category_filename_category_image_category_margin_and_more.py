# Generated by Django 4.0.5 on 2022-09-26 12:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('category', '0004_alter_category_options'),
    ]

    operations = [
        migrations.AddField(
            model_name='category',
            name='filename',
            field=models.CharField(blank=True, help_text='Filename of the generated PDF, please do not include .pdf', max_length=30, verbose_name='File name'),
        ),
        migrations.AddField(
            model_name='category',
            name='image',
            field=models.ImageField(blank=True, help_text='Optional title image of the songbook', null=True, upload_to='uploads/', verbose_name='Title Image'),
        ),
        migrations.AddField(
            model_name='category',
            name='margin',
            field=models.FloatField(default=0, help_text='Margins for title image, might be needed for some printers', verbose_name='Title Image margins'),
        ),
        migrations.AddField(
            model_name='category',
            name='show_date',
            field=models.BooleanField(default=True, help_text='True, if the date should be included in the final PDF', verbose_name='Show date'),
        ),
        migrations.AddField(
            model_name='category',
            name='show_title',
            field=models.BooleanField(default=True, help_text='True, if the title should be shown on the first page', verbose_name='Show title'),
        ),
        migrations.AddField(
            model_name='category',
            name='title',
            field=models.CharField(blank=True, help_text='Name to be used on the title page of the PDF', max_length=100, verbose_name='Title'),
        ),
        migrations.AlterField(
            model_name='category',
            name='locale',
            field=models.CharField(choices=[('en', 'English'), ('cs', 'Česky')], help_text='Language to be used in the generated PDF', max_length=5, verbose_name='Language'),
        ),
    ]