# Generated by Django 2.2.16 on 2020-10-12 14:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('trekking', '0017_auto_20200831_1406'),
    ]

    operations = [
        migrations.CreateModel(
            name='LabelTrek',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('pictogram', models.FileField(max_length=512, null=True, upload_to='upload', verbose_name='Pictogram')),
                ('name', models.CharField(max_length=128, verbose_name='Name')),
                ('description', models.TextField(default='', blank=True, help_text='Description of the label', verbose_name='Description')),
                ('advice', models.TextField(default='', blank=True, help_text='Advice linked with the label', verbose_name='Advices')),
                ('filter_rando', models.BooleanField(default=False, help_text='Show filters portal', verbose_name='Filter rando'))
            ],
            options={
                'verbose_name': 'Trekking Label',
                'verbose_name_plural': 'Trekking Labels',
                'ordering': ['name'],
            },
        ),
        migrations.AddField(
            model_name='trek',
            name='labels',
            field=models.ManyToManyField(blank=True, related_name='labels', to='trekking.LabelTrek', verbose_name='Label'),
        ),
    ]
