# Generated by Django 3.1.4 on 2021-09-09 13:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='enable_email_notifications',
            field=models.BooleanField(default=False, help_text='Enable email notificiations for new reports for this user (irrelevant in case of end users).'),
        ),
    ]