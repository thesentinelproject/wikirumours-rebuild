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
    help = "load user data"

    def handle(self, *args, **kwargs):
        # load user
        import_users()


def import_users():
    dir_path = os.path.dirname(os.path.realpath(__file__))
    # load users
    with transaction.atomic():
        user_csv_file_path = dir_path + '/../data/wikirumours_production_table_wr_users.csv'

        with open(user_csv_file_path, "r") as file:
            reader = csv.DictReader(file)
            for row in reader:
                user_id = row["user_id"].strip()
                username = row["username"].strip()
                password_hash = row["password_hash"].strip()
                password_score = row["password_score"].strip()
                first_name = row["first_name"].strip()
                last_name = row["last_name"].strip()
                email = row["email"].strip()
                primary_phone = row["primary_phone"].strip()
                primary_phone_sms = row["primary_phone_sms"].strip()
                secondary_phone = row["secondary_phone"].strip()
                secondary_phone_sms = row["secondary_phone_sms"].strip()
                country_id = row["country_id"].strip()
                region_id = row["region_id"].strip()
                other_region = row["other_region"].strip()
                city = row["city"].strip()
                is_proxy = row["is_proxy"].strip()
                is_tester = row["is_tester"].strip()
                is_moderator = row["is_moderator"].strip()
                is_community_liaison = row["is_community_liaison"].strip()
                is_administrator = row["is_administrator"].strip()
                registered_on = row["registered_on"].strip()
                registered_by = row["registered_by"].strip()
                referred_by = row["referred_by"].strip()
                last_login = row["last_login"].strip()
                ok_to_contact = row["ok_to_contact"].strip()
                anonymous = row["anonymous"].strip()
                enabled = row["enabled"].strip()
                if not email:
                    email = (
                            "placeholder-"
                            + row['username'].replace('"', "")
                            + "@wikirumours.org"
                    )

                country = Country.objects.filter(
                    iso_code=country_id.replace(' " ', "")
                ).first()

                role = User.END_USER
                if int(is_proxy) == 1:
                    role = User.SUPPORT
                if int(is_moderator) == 1:
                    role = User.MODERATOR
                if int(is_community_liaison) == 1:
                    role = User.COMMUNITY_LIAISON
                if int(is_administrator) == 1:
                    role = User.ADMIN

                date_joined = datetime.datetime.strptime(
                    registered_on, "%Y-%m-%d %H:%M:%S"
                )
                # create user without a password
                _ = User.objects.create_user(
                    id=user_id,
                    username=username.replace('"', ""),
                    first_name=first_name.replace('"', ""),
                    last_name=last_name.replace('"', ""),
                    email=email,
                    phone_number=primary_phone.replace('"', ""),
                    country=country,
                    address=city.replace('"', ""),
                    date_joined=date_joined,
                    role=role,
                    is_user_anonymous=True if anonymous == 1 else False,
                    is_verified=True if enabled == 1 else False,
                )
