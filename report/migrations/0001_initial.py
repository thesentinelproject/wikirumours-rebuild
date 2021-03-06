# Generated by Django 3.1.4 on 2021-09-03 13:33

import colorfield.fields
import django.contrib.gis.db.models.fields
from django.db import migrations, models
import django.db.models.deletion
import report.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='BlogPage',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('internal_title', models.CharField(max_length=200)),
                ('content_slug', models.CharField(max_length=200)),
                ('html_content', models.TextField(blank=True, null=True)),
                ('css_content', models.TextField(blank=True, null=True)),
                ('js_content', models.TextField(blank=True, null=True)),
                ('is_visible', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('sequence_number', models.IntegerField(blank=True, null=True)),
            ],
            options={
                'verbose_name': 'Article',
                'ordering': ['sequence_number'],
            },
        ),
        migrations.CreateModel(
            name='CMSPage',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('internal_title', models.CharField(max_length=200)),
                ('content_slug', models.CharField(max_length=200)),
                ('html_content', models.TextField(blank=True, null=True)),
                ('css_content', models.TextField(blank=True, null=True)),
                ('js_content', models.TextField(blank=True, null=True)),
                ('is_visible', models.BooleanField(default=True)),
                ('show_in_header', models.BooleanField(default=False)),
                ('show_in_footer', models.BooleanField(default=False)),
                ('show_in_sidebar', models.BooleanField(default=False)),
                ('sequence_number', models.IntegerField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Content Block',
                'ordering': ['sequence_number'],
            },
        ),
        migrations.CreateModel(
            name='Comment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('comment', models.TextField()),
                ('is_hidden', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='Domain',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(blank=True, max_length=200, null=True)),
                ('domain', models.CharField(max_length=200)),
                ('is_root_domain', models.BooleanField(default=False)),
                ('logo', models.ImageField(blank=True, null=True, upload_to='', verbose_name='Logo')),
            ],
        ),
        migrations.CreateModel(
            name='FlaggedComment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='OverheardAtChoice',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='PriorityChoice',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, unique=True)),
                ('sequence_number', models.IntegerField(blank=True, null=True)),
                ('number_of_days_before_alert', models.IntegerField(blank=True, help_text='Number of days after which a user should be alerted about reports of this priority level', null=True)),
                ('colour', colorfield.fields.ColorField(default='#FF0000', max_length=18)),
                ('icon', models.CharField(blank=True, help_text='Select a valid unicon descriptor eg: uil-arrow-up', max_length=255, null=True)),
            ],
            options={
                'verbose_name': 'Priority',
                'verbose_name_plural': 'Priorities',
                'ordering': ['sequence_number'],
            },
        ),
        migrations.CreateModel(
            name='Report',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.TextField()),
                ('public_id', models.CharField(default=report.models.generate_public_key, max_length=6, unique=True)),
                ('resolution', models.TextField(blank=True, null=True)),
                ('address', models.CharField(blank=True, max_length=255, null=True)),
                ('location', django.contrib.gis.db.models.fields.PointField(help_text='Use map widget for point the house location', null=True, srid=4326)),
                ('occurred_on', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['-updated_at'],
            },
        ),
        migrations.CreateModel(
            name='ReportedViaChoice',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, unique=True)),
            ],
            options={
                'verbose_name': 'Reported Via',
                'verbose_name_plural': 'Reported Via',
            },
        ),
        migrations.CreateModel(
            name='Sighting',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateTimeField(auto_now=True)),
                ('is_first_sighting', models.BooleanField(default=False)),
                ('address', models.CharField(blank=True, max_length=255, null=True)),
                ('location', django.contrib.gis.db.models.fields.PointField(help_text='Use map to point the location of the sighting.', null=True, srid=4326)),
                ('heard_on', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='SourceChoice',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, unique=True)),
            ],
            options={
                'verbose_name': 'Source',
                'verbose_name_plural': 'Sources',
            },
        ),
        migrations.CreateModel(
            name='StatusChoice',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, unique=True)),
                ('sequence_number', models.IntegerField(blank=True, null=True)),
                ('colour', colorfield.fields.ColorField(default='#FF0000', max_length=18)),
                ('icon', models.CharField(blank=True, help_text='Select a valid unicon descriptor eg: uil-arrow-up', max_length=255, null=True)),
            ],
            options={
                'verbose_name': 'Status',
                'verbose_name_plural': 'Statuses',
                'ordering': ['sequence_number'],
            },
        ),
        migrations.CreateModel(
            name='WatchlistedReport',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('report', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='report.report')),
            ],
            options={
                'verbose_name': 'Watchlisted Report',
                'verbose_name_plural': 'Watchlisted Reports',
            },
        ),
    ]
