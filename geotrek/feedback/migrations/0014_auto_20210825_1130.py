# Generated by Django 3.1.13 on 2021-08-25 11:30

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('feedback', '0013_auto_20210121_0943'),
    ]

    operations = [
        migrations.AddField(
            model_name='report',
            name='created_in_suricate',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Creation date in Suricate'),
        ),
        migrations.AddField(
            model_name='report',
            name='deleted',
            field=models.BooleanField(default=False, editable=False, verbose_name='Deleted'),
        ),
        migrations.AddField(
            model_name='report',
            name='last_updated_in_suricate',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Last updated in Suricate'),
        ),
        migrations.AddField(
            model_name='report',
            name='locked',
            field=models.BooleanField(default=False, verbose_name='Locked'),
        ),
        migrations.AddField(
            model_name='report',
            name='origin',
            field=models.CharField(blank=True, default='unknown', max_length=100, null=True, verbose_name='Origin'),
        ),
        migrations.AddField(
            model_name='report',
            name='uid',
            field=models.UUIDField(blank=True, null=True, unique=True, verbose_name='Identifier'),
        ),
        migrations.AddField(
            model_name='reportstatus',
            name='suricate_id',
            field=models.CharField(blank=True, max_length=100, null=True, unique=True, verbose_name='Identifiant'),
        ),
        migrations.AlterField(
            model_name='reportactivity',
            name='suricate_id',
            field=models.PositiveIntegerField(blank=True, null=True, unique=True, verbose_name='Suricate id'),
        ),
        migrations.AlterField(
            model_name='reportproblemmagnitude',
            name='suricate_id',
            field=models.PositiveIntegerField(blank=True, null=True, unique=True, verbose_name='Suricate id'),
        ),
        migrations.CreateModel(
            name='AttachedMessage',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateTimeField()),
                ('author', models.CharField(max_length=300)),
                ('content', models.TextField()),
                ('suricate_id', models.IntegerField(blank=True, null=True, verbose_name='Identifiant')),
                ('type', models.CharField(max_length=100)),
                ('report', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='feedback.report')),
            ],
            options={
                'unique_together': {('suricate_id', 'date', 'report')},
            },
        ),
    ]