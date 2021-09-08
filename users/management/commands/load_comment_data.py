import csv
import datetime
import os

from django.core.management import BaseCommand
from django.db import transaction

from report.models import Report, Comment
from users.models import User


class Command(BaseCommand):
    help = "load comment data"

    def handle(self, *args, **kwargs):
        import_comments()


def import_comments():
    dir_path = os.path.dirname(os.path.realpath(__file__))

    with transaction.atomic():
        comments_csv_file_path = dir_path + '/../data/wikirumours_production_table_wr_comments.csv'
        with open(comments_csv_file_path, "r") as file:
            reader = csv.DictReader(file)
            for row in reader:
                comment_id = row["comment_id"].strip()
                rumour_id = row["rumour_id"].strip()
                comment = row["comment"].strip()
                created_by = row["created_by"].strip()
                created_on = row["created_on"].strip()
                enabled = row["enabled"].strip()

                user = User.objects.filter(id=int(created_by)).first()
                if user is None:
                    continue
                report = Report.objects.filter(id=int(rumour_id)).first()
                if report is None:
                    continue
                if created_on == "":
                    created_at = datetime.datetime.now()
                else:
                    created_at = datetime.datetime.strptime(
                        created_on, "%Y-%m-%d %H:%M:%S"
                    )

                new_comment = Comment()
                new_comment.id = int(comment_id)
                new_comment.user = user
                new_comment.report = report
                new_comment.is_hidden = True if enabled == 0 else False
                new_comment.comment = comment
                new_comment.created_at = created_at
                new_comment.updated_at = created_at
                new_comment.save()

                saved_comment = Comment.objects.filter(id=int(comment_id)).first()
                saved_comment.created_at = created_at
                saved_comment.save()
