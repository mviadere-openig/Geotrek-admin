# Generated by Django 3.1.14 on 2022-03-28 09:31

from django.db import migrations
import uuid


def gen_uuid(apps, schema_editor):
    model = apps.get_model('feedback', 'report')
    for row in model.objects.all():
        row.uuid = uuid.uuid4()
        row.save(update_fields=['uuid'])


class Migration(migrations.Migration):

    dependencies = [
        ('feedback', '0031_report_eid'),
    ]

    operations = [
        migrations.RunPython(gen_uuid, reverse_code=migrations.RunPython.noop),
    ]