# -*- coding: utf-8 -*-
# Generated by Django 1.11.14 on 2020-03-16 11:45
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


def intervention_sgnage_infrastructure(apps, schema_editor):
    InterventionModel = apps.get_model('maintenance', 'Intervention')
    ContentTypeModel = apps.get_model("contenttypes", "ContentType")
    signage = ContentTypeModel.objects.get(app_label='signage', model='signage')
    infrastructure = ContentTypeModel.objects.get(app_label='infrastructure', model='infrastructure')
    topology = ContentTypeModel.objects.get(app_label='core', model='topology')
    for intervention in InterventionModel.objects.all():
        intervention.target = intervention.topology
        intervention.target_id = intervention.topology.pk
        if intervention.topology.kind == "SIGNAGE":
            intervention.target_type = signage
        elif intervention.topology.kind == "INFRASTRUCTURE":
            intervention.target_type = infrastructure
        else:
            intervention.target_type = topology
        intervention.save()


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('maintenance', '0012_auto_20200311_1608'),
    ]

    operations = [
        migrations.AddField(
            model_name='intervention',
            name='target_type',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='contenttypes.ContentType'),
        ),
        migrations.AddField(
            model_name='intervention',
            name='target_id',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.RunPython(intervention_sgnage_infrastructure),
        migrations.RemoveField(
            model_name='intervention',
            name='topology',
        ),
    ]
