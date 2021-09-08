import csv
import datetime
import os

from django.contrib.gis.geos import Point
from django.core.management import BaseCommand, CommandError
from django.db import transaction
from geopy import Nominatim

from countries.models import Country
from report.models import Report, Sighting, ReportedViaChoice
from users.emails import overdue_reports_reminder
from users.models import User


class Command(BaseCommand):
    help = "compute first sighting"

    def handle(self, *args, **kwargs):
        send_overdue_reminders()


def send_overdue_reminders():
    for user in User.objects.filter(role__in=[User.COMMUNITY_LIAISON, User.MODERATOR, User.ADMIN]):
        if user.enable_email_reminders:
            overdue_tasks = user.get_overdue_tasks()

            if overdue_tasks.count() and user.email:
                overdue_reports_reminder(overdue_tasks, user)
                print(f"Log email reminder sent to {user.email}")

