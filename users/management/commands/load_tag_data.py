import csv
import os

from django.core.management import BaseCommand
from django.db import transaction

from report.models import Report


class Command(BaseCommand):
    help = "load tag data"

    def handle(self, *args, **kwargs):
        import_tags()


def import_tags():
    dir_path = os.path.dirname(os.path.realpath(__file__))
    with transaction.atomic():
        wr_tags_csv_file_path = dir_path + '/../data/wikirumours_production_table_wr_tags.csv'
        wr_rumour_x_tags_csv_file_path = dir_path + '/../data/wikirumours_production_table_wr_rumours_x_tags.csv'

        tags = {}
        with open(wr_tags_csv_file_path, "r") as wr_tags_csv_file:
            reader = csv.DictReader(wr_tags_csv_file)
            for row in reader:
                tag_id = row["tag_id"].strip()
                tag = row["tag"].strip()
                created_by = row["created_by"].strip()
                created_on = row["created_on"].strip()
                tags[tag_id] = tag

        with open(wr_rumour_x_tags_csv_file_path, "r") as wr_rumour_x_tags_csv_file:
            reader = csv.DictReader(wr_rumour_x_tags_csv_file)
            for row in reader:
                rumour_id = row["rumour_id"].strip()
                tag_id = row["tag_id"].strip()
                added_by = row["added_by"].strip()
                added_on = row["added_on"].strip()

                report = Report.objects.filter(id=int(rumour_id)).first()
                if report is None:
                    continue
                tag = tags.get(tag_id, None)
                if tag:
                    report.tags.add(tag)
