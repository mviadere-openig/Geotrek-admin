# Generated by Django 3.2.18 on 2023-05-03 08:37

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('outdoor', '0043_auto_20230407_0943'),
    ]

    operations = [
        migrations.AlterField(
            model_name='practice',
            name='sector',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='practices', to='outdoor.sector', verbose_name='Sector'),
        ),
    ]
