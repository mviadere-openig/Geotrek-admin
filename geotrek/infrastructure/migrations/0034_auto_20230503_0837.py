# Generated by Django 3.2.18 on 2023-05-03 08:37

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('authent', '0011_alter_userprofile_structure'),
        ('infrastructure', '0033_auto_20230407_0943'),
    ]

    operations = [
        migrations.AlterField(
            model_name='infrastructurecondition',
            name='structure',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='authent.structure', verbose_name='Related structure'),
        ),
        migrations.AlterField(
            model_name='infrastructuremaintenancedifficultylevel',
            name='structure',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='authent.structure', verbose_name='Related structure'),
        ),
        migrations.AlterField(
            model_name='infrastructuretype',
            name='structure',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='authent.structure', verbose_name='Related structure'),
        ),
        migrations.AlterField(
            model_name='infrastructureusagedifficultylevel',
            name='structure',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='authent.structure', verbose_name='Related structure'),
        ),
    ]