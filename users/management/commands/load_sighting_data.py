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
    help = "load sighting data"

    def handle(self, *args, **kwargs):
        import_sightings()


def import_sightings():
    with transaction.atomic():
        dir_path = os.path.dirname(os.path.realpath(__file__))
        # load users
        with transaction.atomic():
            sightings_csv_file_path = dir_path + '/../data/wikirumours_production_table_wr_rumour_sightings.csv'

            with open(sightings_csv_file_path, "r") as file:
                reader = csv.DictReader(x.replace('\0', '') for x in file)
                for row in reader:
                    sighting_id = row["sighting_id"].strip()
                    public_id = row["public_id"].strip()
                    rumour_id = row["rumour_id"].strip()
                    details = row["details"].strip()
                    heard_on = row["heard_on"].strip()
                    country_id = row["country_id"].strip()
                    city = row["city"].strip()
                    location_type = row["location_type"].strip()
                    latitude = row["latitude"].strip()
                    longitude = row["longitude"].strip()
                    unable_to_geocode = row["unable_to_geocode"].strip()
                    source_id = row["source_id"].strip()
                    ipv4 = row["ipv4"].strip()
                    ipv6 = row["ipv6"].strip()
                    created_by = row["created_by"].strip()
                    entered_by = row["entered_by"].strip()
                    entered_on = row["entered_on"].strip()

                    user = User.objects.filter(id=created_by).first()
                    if user is None:
                        continue
                    report = Report.objects.filter(id=rumour_id).first()
                    if report is None:
                        continue

                    else:
                        latitude = float(latitude)
                        longitude = float(longitude)
                        address = city

                        if not heard_on or heard_on[0] == '0':
                            heard_on = None
                        else:
                            try:
                                heard_on = datetime.datetime.strptime(
                                    heard_on, "%Y-%m-%d %H:%M:%S"
                                )
                            except:
                                heard_on = None
                        created_at = datetime.datetime.strptime(
                            entered_on, "%Y-%m-%d %H:%M:%S"
                        )
                        country = Country.objects.filter(
                            iso_code=country_id.replace('"', "")
                        ).first()

                        reported_via = ReportedViaChoice.objects.filter(id=source_id).first()

                        sighting = Sighting()
                        sighting.id = int(sighting_id)
                        sighting.report = report
                        sighting.user = user
                        sighting.heard_on = heard_on
                        sighting.reported_via = reported_via
                        sighting.address = address
                        sighting.country = country
                        sighting.source = None
                        sighting.overheard_at = None
                        sighting.location = Point(longitude, latitude)
                        sighting.is_first_sighting = False
                        sighting.save()

                        sighting.created_at = created_at
                        sighting.save()

