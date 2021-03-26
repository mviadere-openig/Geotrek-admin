# Generated by Django 3.1.7 on 2021-03-15 15:12

from django.db import migrations
import json


def serialize_orientation(apps, schema_editor):
    Site = apps.get_model('outdoor', 'Site')
    for site in Site.objects.all():
        site.orientation = json.dumps(site.orientation.split(',') if site.orientation else [])
        site.wind = json.dumps(site.wind.split(',') if site.wind else [])
        site.save()


class Migration(migrations.Migration):

    dependencies = [
        ('outdoor', '0019_auto_20210311_1101'),
    ]

    operations = [
        migrations.RunPython(serialize_orientation),
    ]