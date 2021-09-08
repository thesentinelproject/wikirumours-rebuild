from django.core.management.base import BaseCommand

from users.management.commands.compute_first_sighting import compute_first_sighting
from users.management.commands.load_comment_data import import_comments
from users.management.commands.load_master_tables import import_master_tables
from users.management.commands.load_report_evidence import import_report_evidence
from users.management.commands.load_rumour_data import import_rumours
from users.management.commands.load_sighting_data import import_sightings
from users.management.commands.load_tag_data import import_tags
from users.management.commands.load_user_data import import_users
from users.management.commands.load_watchlist_data import import_watchlists


class Command(BaseCommand):
    help = "Load data from all csvs"

    def handle(self, *args, **kwargs):
        import_master_tables()
        import_users()
        import_rumours()
        import_sightings()
        compute_first_sighting()
        import_comments()
        import_tags()
        import_watchlists()
        import_report_evidence()

