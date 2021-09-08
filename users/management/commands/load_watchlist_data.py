import csv
import os
import datetime
from django.core.management import BaseCommand
from django.db import transaction

from report.models import Report, WatchlistedReport
from users.models import User


class Command(BaseCommand):
    help = "load watchlist data"

    def handle(self, *args, **kwargs):
        import_watchlists()


def import_watchlists():
    dir_path = os.path.dirname(os.path.realpath(__file__))
    with transaction.atomic():
        wr_watchlist_csv_file_path = dir_path + '/../data/wikirumours_production_table_wr_watchlist.csv'

        with open(wr_watchlist_csv_file_path, "r") as wr_watchlist_csv_file:
            reader = csv.DictReader(wr_watchlist_csv_file)
            for row in reader:
                rumour_id = row["rumour_id"].strip()
                created_by = row["created_by"].strip()
                created_on = row["created_on"].strip()
                notify_of_updates = row["notify_of_updates"].strip()
                if created_on == "":
                    created_at = datetime.datetime.now()
                else:
                    created_at = datetime.datetime.strptime(
                        created_on, "%Y-%m-%d %H:%M:%S"
                    )

                report = Report.objects.filter(id=int(rumour_id)).first()
                user = User.objects.filter(id=int(created_by)).first()
                if report is None or user is None:
                    continue

                new_watchlisted_report = WatchlistedReport()
                new_watchlisted_report.user = user
                new_watchlisted_report.report = report
                new_watchlisted_report.save()

                new_watchlisted_report.created_at = created_at
                new_watchlisted_report.save()
