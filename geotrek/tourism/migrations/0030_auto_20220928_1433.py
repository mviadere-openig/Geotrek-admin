# Generated by Django 3.2.15 on 2022-09-28 14:33

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('tourism', '0029_auto_20220927_0901'),
    ]

    operations = [
        migrations.CreateModel(
            name='CancellationReason',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('label', models.CharField(max_length=128, verbose_name='Label')),
            ],
            options={
                'verbose_name': 'Cancellation reason',
                'verbose_name_plural': 'Cancellation reasons',
            },
        ),
        migrations.AddField(
            model_name='touristicevent',
            name='cancelled',
            field=models.BooleanField(default=False, help_text='Boolean indicating if Event is cancelled', verbose_name='Cancelled'),
        ),
        migrations.AddField(
            model_name='touristicevent',
            name='cancellation_reason',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='touristic_events', to='tourism.cancellationreason', verbose_name='Cancellation reason'),
        ),
    ]
