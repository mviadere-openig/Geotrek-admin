# Generated by Django 3.1.14 on 2022-02-03 13:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('outdoor', '0037_course_accessibility'),
    ]

    operations = [
        migrations.AddField(
            model_name='site',
            name='accessibility',
            field=models.TextField(blank=True, verbose_name='Accessibility'),
        ),
    ]
