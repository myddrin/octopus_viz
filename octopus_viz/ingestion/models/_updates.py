import logging
from datetime import date, time
from typing import Tuple

from django.db import transaction
from django.db.models import QuerySet, Q

from ingestion import models


DetachedKey = Tuple[date, date, models.Direction]
DetachedValues = list[models.Consumption]


class UpdateConsumption:
    def __init__(self, logger: logging.Logger | None, pretend: bool = False):
        if logger is None:
            logger = logging.getLogger(__name__)
        self.logger = logger
        self.pretend = pretend

    @classmethod
    def all_rows(cls) -> QuerySet:
        return models.Consumption.objects.select_for_update()

    @classmethod
    def detached_rows(cls, query: QuerySet | None) -> QuerySet:
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
        It's still high inefficient :(
        :return:
        """
        if query is None:
            query = cls.all_rows()
        return query.filter(
            tariff__isnull=True,
        )

    @classmethod
    def related_tariff(cls, valid_from: date, valid_until: date, direction: models.Direction) -> models.Tariff | None:
        # That did not work anyway
        # return queryset.filter(
        #     tariff__valid_from_lte=F('consumption__interval_start'),
        #     tariff__valid_until_gt=F('consumption__interval_end'),
        # ).values('tariff__id')
        try:
            return models.Tariff.objects.filter(
                Q(valid_from__lte=valid_from),
                Q(valid_until__isnull=True) | Q(valid_until__gte=valid_until),
                Q(direction=direction),
            )[0]
        except IndexError:
            return None

    @classmethod
    def related_rates(cls, valid_from: date, valid_until: date, direction: models.Direction) -> QuerySet:
        return (
            models.Rate.objects.select_related('tariff')
            .filter(
                Q(tariff__valid_from__lte=valid_from),
                Q(tariff__valid_until__isnull=True) | Q(tariff__valid_until__gte=valid_until),
                Q(tariff__direction=direction),
            )
            .order_by('interval_from', 'interval_end')
        )

    def _update_row(self, row: models.Consumption, tariff: models.Tariff | None, best_rate: models.Rate | None) -> int:
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

    def _update_detached_rows(self, detached_rows: dict[DetachedKey, DetachedValues]) -> int:
        no_rates = 0
        for key, rows in detached_rows.items():
            rates: list[models.Rate] = list(self.related_rates(key[0], key[1], key[2]))
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
                        f' [{detached.interval_start.time()} ; {detached.interval_end.time()}] has no rate',
                    )
                no_rates += n

        return no_rates

    def update_rows(self, all_rows=False):
        with transaction.atomic():
            # TODO(tr) I would really like to do the select with a single query...
            detached_rows: dict[DetachedKey, DetachedValues] = {}
            if all_rows:
                self.logger.info('Updating all consumption rows...')
                consider_rows = self.all_rows()
            else:
                self.logger.info('Updating detached consumption rows...')
                consider_rows = self.detached_rows()

            found = 0
            for row in consider_rows:  # type: models.Consumption
                key = row.interval_start.date(), row.interval_end.date(), row.meter.mpan.direction
                detached_rows.setdefault(key, [])
                detached_rows[key].append(row)
                found += 1

            self.logger.info(f'  Found {found} rows to update')
            no_rates = self._update_detached_rows(detached_rows)
            self.logger.info(f'  Updated {found - no_rates} with rates ({no_rates} did not have rates)')