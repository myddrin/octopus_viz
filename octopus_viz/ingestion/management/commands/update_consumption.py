from django.core.management import BaseCommand

from ._utils import CommandAsLogger
from ingestion.models import UpdateConsumption


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            '--all-rows',
            action='store_true',
        )
        parser.add_argument(
            '--pretend',
            action='store_true',
        )

    def handle(self, all_rows: bool, pretend: bool, **kwargs):
        update = UpdateConsumption(
            logger=CommandAsLogger(self),
            pretend=pretend,
        )

        update.gather_and_update_rows(all_rows)
