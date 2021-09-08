import csv
import datetime
import os

from django.contrib.gis.geos import Point
from django.core.management import BaseCommand
from django.db import transaction

from countries.models import Country
from report.models import Domain, Report, PriorityChoice, StatusChoice
from users.models import User


class Command(BaseCommand):
    help = "load rumour data"

    def handle(self, *args, **kwargs):
        # load rumours
        import_rumours()


def import_rumours():
    # load rumours
    dir_path = os.path.dirname(os.path.realpath(__file__))
    with transaction.atomic():
        rumours_csv_fie_path = dir_path + '/../data/wikirumours_production_table_wr_rumours.csv'
        with open(rumours_csv_fie_path, "r") as file:
            reader = csv.DictReader(file)
            for row in reader:
                rumour_id = row["rumour_id"].strip()
                public_id = row["public_id"].strip()
                domain_alias_id = row["domain_alias_id"].strip()
                description = row["description"].strip()
                country_id = row["country_id"].strip()
                city = row["city"].strip()
                latitude = row["latitude"].strip()
                longitude = row["longitude"].strip()
                unable_to_geocode = row["unable_to_geocode"].strip()
                occurred_on_row = row["occurred_on"].strip()
                created_by = row["created_by"].strip()
                entered_by = row["entered_by"].strip()
                created_on = row["created_on"].strip()
                updated_on = row["updated_on"].strip()
                updated_by = row["updated_by"].strip()
                priority_id = row["priority_id"].strip()
                status_id = row["status_id"].strip()
                findings = row["findings"].strip()
                verified_with = row["verified_with"].strip()
                photo_evidence_file_ext = row["photo_evidence_file_ext"].strip()
                assigned_to = row["assigned_to"].strip()
                enabled = row["enabled"].strip()

                latitude = float(latitude)
                longitude = float(longitude)
                address = city

                occurred_on = None
                if occurred_on_row == "" or occurred_on_row[0] == '0':
                    occurred_on = None
                else:
                    occurred_on = datetime.datetime.strptime(
                        occurred_on_row, "%Y-%m-%d %H:%M:%S"
                    )

                country = Country.objects.filter(
                    iso_code=country_id
                ).first()

                domain = Domain.objects.filter(id=domain_alias_id).first()

                # note: ids need to match for this. is expected to work on a fresh database
                priority = PriorityChoice.objects.filter(id=priority_id).first()
                status = StatusChoice.objects.filter(id=status_id).first()

                if int(domain_alias_id) == 0:
                    domain = Domain.objects.filter(id=1).first()

                user = User.objects.filter(id=created_by).first()
                recently_updated_user = User.objects.filter(id=updated_by).first()
                assigned_to = User.objects.filter(id=assigned_to).first()

                report = Report()
                report.id = int(rumour_id)
                report.domain = domain
                report.title = description
                report.public_id = public_id
                report.address = address
                report.location = Point(longitude, latitude)
                report.occurred_on = occurred_on
                report.reported_by = user
                report.country = country
                report.created_at = datetime.datetime.strptime(
                    created_on, "%Y-%m-%d %H:%M:%S"
                )
                updated_at = datetime.datetime.strptime(
                    updated_on, "%Y-%m-%d %H:%M:%S"
                )
                report.recently_edited_by = recently_updated_user
                report.priority = priority
                report.status = status
                report.resolution = (
                    findings
                )
                report.assigned_to = assigned_to
                print("--------------------------------------------------")
                print(f"{report.id} {report.public_id}")
                print("--------------------------------------------------")
                report.save()

                Report.objects.filter(id=report.id).update(updated_at=updated_at)
