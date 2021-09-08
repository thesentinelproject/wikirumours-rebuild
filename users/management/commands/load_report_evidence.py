import csv
import os
import datetime
from typing import re

from django.core.files import File
from django.core.management import BaseCommand
from django.db import transaction
from django.utils.encoding import force_text
from django.utils.functional import keep_lazy_text

from report.models import Report, WatchlistedReport, EvidenceFile
from users.models import User


class Command(BaseCommand):
    help = "load report evidence"

    def handle(self, *args, **kwargs):
        import_report_evidence()


def import_report_evidence():
    dir_path = os.path.dirname(os.path.realpath(__file__))
    with transaction.atomic():
        report_evidence_folder = dir_path + '/../data/media/'
        # report_evidence_folder = dir_path + '/../../../wikirumours/media/'
        directories = os.listdir(report_evidence_folder)
        for folder in directories:
            report_folder_path = os.path.join(report_evidence_folder, folder)
            if os.path.isfile(report_folder_path):
                continue
            report_public_id = folder
            report = Report.objects.filter(public_id=report_public_id).first()
            if not report:
                continue
            process_report_folder(report, report_folder_path)


def process_report_folder(report, report_folder_path):
    files = os.listdir(report_folder_path)
    for file in files:
        existing_file_path = os.path.join(report_folder_path, file)
        if os.path.isfile(existing_file_path):
            with open(existing_file_path, 'rb') as f:
                evidence_file = EvidenceFile(
                    report=report,
                    uploader=None,
                    file=File(f, name=file)
                )
                evidence_file.save()
    return


@keep_lazy_text
def get_valid_filename(s):
    """
    Returns the given string converted to a string that can be used for a clean
    filename. Specifically, leading and trailing spaces are removed; other
    spaces are converted to underscores; and anything that is not a unicode
    alphanumeric, dash, underscore, or dot, is removed.
    """
    s = force_text(s).strip().replace(' ', '_')
    return re.sub(r'(?u)[^-\w.]', '', s)
