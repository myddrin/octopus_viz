from datetime import date

from django.core.management import BaseCommand
from django.utils import timezone

from ingestion.models import IngestConsumption

from ._utils import CommandAsLogger


class Command(BaseCommand):
    help = 'Download data from Octopus for a particular MPAN'

    def add_arguments(self, parser):
        parser.add_argument(
            '--period-from',
            type=str,
            default=None,
            help=(
                'Download data starting from this date (YYYY-MM-DD) - inclusive. '
                'No date means the last found date for the meter.'
            ),
        )
        parser.add_argument(
            '--period-to',
            type=str,
            default=None,
            help=('Download data ending on that date (YYYY-MM-DD) - exclusive.No date means today.'),
        )
        parser.add_argument(
            '--meter-mpan',
            type=str,
            default=None,
            help='Explicit MPAN to download data for',
        )
        parser.add_argument(
            '--pretend',
            action='store_true',
            help='Do not connect to the Octopus API',
        )

    @classmethod
    def handle_date(cls, value: str | None) -> date | None:
        if value is None:
            return None
        return date.fromisoformat(value)

    def handle(
        self,
        period_from: str | None = None,
        period_to: str | None = None,
        meter_mpan: str | None = None,
        pretend: bool = False,
        **options,
    ):
        start = self.handle_date(period_from)
        end = self.handle_date(period_to) or timezone.now().date()

        IngestConsumption(CommandAsLogger(self), pretend=pretend).ingest(
            start,
            end,
            meter_mpan=meter_mpan,
        )
