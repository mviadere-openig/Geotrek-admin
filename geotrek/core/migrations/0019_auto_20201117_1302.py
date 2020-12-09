# Generated by Django 3.1.3 on 2020-11-17 13:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0018_remove_other_objects_from_factories'),
    ]

    operations = [
        migrations.AlterField(
            model_name='path',
            name='date_insert',
            field=models.DateTimeField(auto_now_add=True, verbose_name="Date d'insertion"),
        ),
        migrations.AlterField(
            model_name='path',
            name='date_update',
            field=models.DateTimeField(auto_now=True, db_index=True, verbose_name='Date de modification'),
        ),
        migrations.AlterField(
            model_name='topology',
            name='date_insert',
            field=models.DateTimeField(auto_now_add=True, verbose_name="Date d'insertion"),
        ),
        migrations.AlterField(
            model_name='topology',
            name='date_update',
            field=models.DateTimeField(auto_now=True, db_index=True, verbose_name='Date de modification'),
        ),
        migrations.AlterField(
            model_name='topology',
            name='deleted',
            field=models.BooleanField(default=False, editable=False, verbose_name='Supprimé'),
        ),
    ]