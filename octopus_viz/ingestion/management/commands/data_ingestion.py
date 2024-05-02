from datetime import date

from django.core.management import BaseCommand
from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone

from ingestion import models
from ingestion.models import UpdateConsumption
from ingestion.octopus_client.api import OctopusAPI

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
    def _list_meters(cls, meter_mpan: str | None) -> QuerySet:
        queryset = models.MeterFilters.meters_with_api_key()
        if meter_mpan is not None:
            queryset = queryset.filter(mpan=meter_mpan)
        return queryset

    @classmethod
    def _get_last_entry(cls, meter: models.Meter) -> date:
        latest = models.MeterFilters(meter).get_latest_consumption()
        if latest is None:
            raise RuntimeError(f'No latest entry for {meter}')
        return latest.interval_end.date()

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
        period_from = self.handle_date(period_from)
        period_to = self.handle_date(period_to)
        if period_to is None:
            period_to = timezone.now().date()
        found_meters = 0
        update_rows = UpdateConsumption(CommandAsLogger(self))

        for found_meters, meter in enumerate(self._list_meters(meter_mpan), start=1):  # type: int, models.Meter
            if period_from is None:
                period_from = self._get_last_entry(meter)

            api_connection = OctopusAPI(meter)

            self.stdout.write(
                f'Download data for {meter} period_from={period_from.isoformat()} period_to={period_to.isoformat()}',
            )
            if pretend:
                self.stdout.write(f'PRETEND: download data from: {api_connection.consumption_endpoint}')
                continue  # skip the actual downloading

            with transaction.atomic():
                found_rows = 0
                for found_rows, data in enumerate(api_connection.get_consumption_data(period_from, period_to), start=1):  # type: int, dict
                    new_row = api_connection.build_consumption_from_json(data)
                    update_rows.add_detached_row(new_row)

                self.stdout.write(f'Attaching {found_rows} rows for {meter}...')
                no_rate = update_rows.update_detached_rows()
                self.stdout.write(f'Linked {found_rows - no_rate} rows to a rate')

        self.stdout.write(f'Found {found_meters} meters to get data from')
