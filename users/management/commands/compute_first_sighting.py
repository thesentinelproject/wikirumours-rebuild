import csv
import datetime
import os

from django.contrib.gis.geos import Point
from django.core.management import BaseCommand, CommandError
from django.db import transaction
from geopy import Nominatim

from countries.models import Country
from report.models import Report, Sighting, ReportedViaChoice
from users.models import User


class Command(BaseCommand):
    help = "compute first sighting"

    def handle(self, *args, **kwargs):
        compute_first_sighting()


def compute_first_sighting():
    with transaction.atomic():
        reports = Report.objects.all()
        # print("Total reports : " + str(len(reports)))
        for index, report in enumerate(reports):
            # print("Report " + str(index + 1) + "/" + str(len(reports)))
            sighting = Sighting.objects.filter(report=report).order_by("heard_on").first()
            if sighting:
                Sighting.objects.filter(report=report).update(is_first_sighting=False)
                sighting.is_first_sighting = True
                sighting.save()
