# Generated by Django 3.1.13 on 2021-09-08 13:06

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('infrastructure', '0025_auto_20210721_1540'),
    ]

    operations = [
        migrations.AlterField(
            model_name='infrastructure',
            name='type',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='infrastructures', to='infrastructure.infrastructuretype', verbose_name='Type'),
        ),
    ]
