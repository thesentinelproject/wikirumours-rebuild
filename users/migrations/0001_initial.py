# Generated by Django 3.1.4 on 2021-09-03 13:33

import django.contrib.auth.models
import django.contrib.auth.validators
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import users.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('report', '0001_initial'),
        ('countries', '0001_initial'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='AccountActivationToken',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('email', models.EmailField(max_length=255)),
                ('token', models.CharField(default=users.models.generate_password_reset_token, max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='BlacklistedIP',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ip_address', models.GenericIPAddressField()),
            ],
            options={
                'verbose_name': 'Blacklisted IP',
                'verbose_name_plural': 'Blacklisted IPs',
            },
        ),
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('username', models.CharField(error_messages={'unique': 'A user with that username already exists.'}, help_text='Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.', max_length=150, unique=True, validators=[django.contrib.auth.validators.UnicodeUsernameValidator()], verbose_name='username')),
                ('first_name', models.CharField(blank=True, max_length=150, verbose_name='first name')),
                ('last_name', models.CharField(blank=True, max_length=150, verbose_name='last name')),
                ('is_staff', models.BooleanField(default=False, help_text='Designates whether the user can log into this admin site.', verbose_name='staff status')),
                ('is_active', models.BooleanField(default=True, help_text='Designates whether this user should be treated as active. Unselect this instead of deleting accounts.', verbose_name='active')),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now, verbose_name='date joined')),
                ('phone_number', models.CharField(blank=True, max_length=20)),
                ('email', models.EmailField(error_messages={'unique': 'A user with that email already exists.'}, max_length=254, unique=True, verbose_name='email address')),
                ('api_key', models.CharField(blank=True, max_length=20, null=True)),
                ('is_verified', models.BooleanField(default=False)),
                ('is_user_anonymous', models.BooleanField(default=False, help_text='If this is set to true, your name will not be displayed on reports submitted by you.')),
                ('is_dark_mode_enabled', models.BooleanField(default=False)),
                ('address', models.CharField(blank=True, max_length=250, null=True)),
                ('location', models.CharField(blank=True, max_length=20, null=True)),
                ('role', models.CharField(choices=[('End User', 'End User'), ('Support', 'Support'), ('Moderator', 'Moderator'), ('Community Liaison', 'Community Liaison'), ('Admin', 'Admin')], default='End User', max_length=200)),
                ('enable_email_reminders', models.BooleanField(default=False, help_text='Enable email reminders for overdue tasks for this user (irrelevant in case of end users).')),
                ('api_post_access', models.BooleanField(default=False, help_text='Allowed to create POST requests via API')),
                ('country', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='countries.country')),
                ('groups', models.ManyToManyField(blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', related_name='user_set', related_query_name='user', to='auth.Group', verbose_name='groups')),
                ('role_domains', models.ManyToManyField(blank=True, to='report.Domain')),
                ('sign_up_domain', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='user_assigned_to', to='report.domain')),
                ('user_permissions', models.ManyToManyField(blank=True, help_text='Specific permissions for this user.', related_name='user_set', related_query_name='user', to='auth.Permission', verbose_name='user permissions')),
                ('watchlisted_reports', models.ManyToManyField(blank=True, to='report.Report')),
            ],
            options={
                'verbose_name': 'user',
                'verbose_name_plural': 'users',
                'abstract': False,
            },
            managers=[
                ('objects', django.contrib.auth.models.UserManager()),
            ],
        ),
    ]
