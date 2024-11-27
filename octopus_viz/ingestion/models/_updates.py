import json
import logging
from datetime import date, time
from typing import Tuple

from django.db import transaction
from django.db.models import QuerySet, Q

from ._meter import Meter
from ._tariff import Tariff, Rate
from ._enums import Direction
from ._consumption import Consumption
from ._filters import MeterFilters
from ..octopus_client.api import OctopusAPI

DetachedKey = Tuple[date, date, Direction]
DetachedValues = list[Consumption]


class UpdateConsumption:
    def __init__(self, logger: logging.Logger | None, pretend: bool = False):
        if logger is None:
            logger = logging.getLogger(__name__)
        self.logger = logger
        self.pretend = pretend
        self.detached_rows: dict[DetachedKey, DetachedValues] = {}

    @classmethod
    def all_rows(cls) -> QuerySet:
        return Consumption.objects.select_for_update()

    @classmethod
    def gather_detached_rows(cls, query: QuerySet | None = None) -> QuerySet:
        """
        select * from ingestion_consumption where rate_id is null;

        I wanted to do something like:
        select * from ingestion_consumption
        join ingestion_tariff on (
        ingestion_consumption.interval_start >= ingestion_tariff.valid_from
        and (ingestion_tariff.valid_until is null or
          ingestion_consumption.interval_end < ingestion_tariff.valid_until)
        )
        where ingestion_consumption.rate_id is null

        but I could not - instead I'll make a select_for_update and rely on the transaction.
        It's still highly inefficient :(
        :return:
        """
        if query is None:
            query = cls.all_rows()
        return query.filter(
            tariff__isnull=True,
        )

    @classmethod
    def related_tariff(cls, valid_from: date, valid_until: date, direction: Direction) -> Tariff | None:
        # That did not work anyway
        # return queryset.filter(
        #     tariff__valid_from_lte=F('consumption__interval_start'),
        #     tariff__valid_until_gt=F('consumption__interval_start'),
        # ).values('tariff__id')
        try:
            return Tariff.objects.filter(
                Q(valid_from__lte=valid_from),
                Q(valid_until__isnull=True) | Q(valid_until__gt=valid_from),
                Q(direction=direction),
            )[0]
        except IndexError:
            return None

    @classmethod
    def related_rates(cls, valid_from: date, valid_until: date, direction: Direction) -> QuerySet:
        return (
            Rate.objects.select_related('tariff')
            .filter(
                Q(tariff__valid_from__lte=valid_from),
                Q(tariff__valid_until__isnull=True) | Q(tariff__valid_until__gt=valid_from),
                Q(tariff__direction=direction),
            )
            .order_by('interval_from', 'interval_end')
        )

    def _update_row(self, row: Consumption, tariff: Tariff | None, best_rate: Rate | None) -> int:
        row.tariff = tariff
        if best_rate is None:
            self.logger.warning(f'  No rate found for {row}, setting {tariff=}')
            no_rates = 1
        else:
            row.rate = best_rate
            no_rates = 0

        if not self.pretend:
            row.save()

        return no_rates

    def update_detached_rows(self) -> int:
        no_rates = 0
        for key, rows in self.detached_rows.items():
            rates: list[Rate] = list(self.related_rates(key[0], key[1], key[2]))
            if not rates:
                tariff = self.related_tariff(key[0], key[1], key[2])
            else:
                tariff = rates[0].tariff

            for detached in rows:
                best_rate = None
                detached_start = detached.interval_start.time()
                detached_end = detached.interval_end.time()
                for rate in rates:
                    if rate.interval_from > detached_start:
                        continue

                    if rate.interval_end == time(0, 0) and detached_start >= rate.interval_from:
                        best_rate = rate
                    elif rate.interval_end >= detached_end:
                        best_rate = rate

                    if best_rate is not None:
                        break

                n = self._update_row(detached, tariff, best_rate)
                if n:  # debug
                    self.logger.info(
                        f' [{detached.interval_start} ; {detached.interval_end.time()}] has no rate',
                    )
                no_rates += n

        self.detached_rows = {}
        return no_rates

    @classmethod
    def build_row_key(cls, row: Consumption) -> DetachedKey:
        valid_from = row.interval_start.date()
        valid_until = row.interval_end.date()
        return valid_from, valid_until, row.meter.mpan.direction

    def add_detached_row(self, row: Consumption):
        key = self.build_row_key(row)
        self.detached_rows.setdefault(key, [])
        self.detached_rows[key].append(row)

    def gather_and_update_rows(self, all_rows=False):
        with transaction.atomic():
            # TODO(tr) I would really like to do the select with a single query...
            self.detached_rows = {}
            if all_rows:
                self.logger.info('Updating all consumption rows...')
                consider_rows = self.all_rows()
            else:
                self.logger.info('Updating detached consumption rows...')
                consider_rows = self.gather_detached_rows()

            found = 0
            for row in consider_rows:  # type: Consumption
                self.add_detached_row(row)
                found += 1

            self.logger.info(f'  Found {found} rows to update')
            no_rates = self.update_detached_rows()
            self.logger.info(f'  Updated {found - no_rates} with rates ({no_rates} did not have rates)')


class IngestConsumption:
    @classmethod
    def _list_meters(cls, meter_mpan: str | None) -> QuerySet:
        queryset = MeterFilters.meters_with_api_key()
        if meter_mpan is not None:
            queryset = queryset.filter(mpan=meter_mpan)
        return queryset

    @classmethod
    def _get_last_entry(cls, meter: Meter) -> date:
        latest = MeterFilters(meter).get_latest_consumption()
        if latest is None:
            raise RuntimeError(f'No latest entry for {meter}')
        return latest.interval_end.date()

    def __init__(self, logger: logging.Logger | None, *, pretend: bool = False, debug_filename: str | None = None):
        if logger is None:
            logger = logging.getLogger(__name__)
        self.logger = logger
        self.pretend = pretend
        self.debug_filename = debug_filename

    def _ingest_in_db(
        self,
        meter: 'Meter',
        period_from: date | None,
        period_to: date | None,
        *,
        api_connection: OctopusAPI,
        update_rows: UpdateConsumption,
    ) -> int:
        with transaction.atomic():
            found_rows = 0
            for found_rows, data in enumerate(
                api_connection.get_consumption_data(period_from, period_to),
                start=1,
            ):  # type: int, dict
                new_row = api_connection.build_consumption_from_json(data)
                update_rows.add_detached_row(new_row)

            self.logger.info(f'Attaching {found_rows} rows for {meter}...')
            no_rate = update_rows.update_detached_rows()
            self.logger.info(f'Linked {found_rows - no_rate} rows to a rate for {meter}')
        return found_rows

    def _append_to_file(
        self,
        meter: 'Meter',
        period_from: date | None,
        period_to: date | None,
        *,
        api_connection: OctopusAPI,
        filename: str,
    ) -> int:
        found_rows = 0
        self.logger.info(f'Writing results for {meter} into {filename}')
        with open(filename, 'a') as file:
            for found_rows, data in enumerate(
                api_connection.get_consumption_data(period_from, period_to),
                start=1,
            ):  # type: int, dict
                data['mpan'] = meter.mpan.mpan
                data['serial'] = meter.serial
                data['direction'] = meter.mpan.direction
                file.write(json.dumps(data, sort_keys=True) + '\n')

        return found_rows

    def ingest(self, period_from: date | None, period_to: date, *, meter_mpan: str | None = None):
        found_meters = 0
        update_rows = UpdateConsumption(self.logger)
        total_rows = 0

        for found_meters, meter in enumerate(self._list_meters(meter_mpan), start=1):  # type: int, models.Meter
            if period_from is None:
                period_from = self._get_last_entry(meter)

            api_connection = OctopusAPI(meter, logger=self.logger)

            self.logger.info(
                f'Download data for {meter} period_from={period_from.isoformat()} period_to={period_to.isoformat()}',
            )
            if self.pretend:
                self.logger.info(f'PRETEND: download data from: {api_connection.consumption_endpoint}')
                # skip the actual downloading
            elif self.debug_filename is not None:
                total_rows += self._append_to_file(
                    meter,
                    period_from,
                    period_to,
                    api_connection=api_connection,
                    filename=self.debug_filename,
                )
            else:
                total_rows += self._ingest_in_db(
                    meter,
                    period_from,
                    period_to,
                    api_connection=api_connection,
                    update_rows=update_rows,
                )

        self.logger.info(f'Found {found_meters} meters and downloaded {total_rows} rows')
