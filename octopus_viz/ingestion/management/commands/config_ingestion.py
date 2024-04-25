import dataclasses
import json
import logging
from datetime import time, datetime
from operator import attrgetter
from typing import Self

from django.core.management import BaseCommand
from django.db import transaction

from ingestion import models

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class RateObject:
    interval_from: time
    interval_end: time
    unit_rate: float

    @classmethod
    def from_list(cls, json_list: list[dict]) -> list[Self]:
        data = []

        for obj in json_list:
            logger.warning(f'  loading {obj}')
            interval_start_hour, interval_start_minute = map(int, obj['interval_start'].split(':'))
            interval_end_hour, interval_end_minute = map(int, obj['interval_end'].split(':'))
            data.append(
                cls(
                    time(hour=interval_start_hour, minute=interval_start_minute),
                    # because in file 24:00 is used for tomorrow 00:00
                    time(hour=interval_end_hour % 24, minute=interval_end_minute),
                    obj['rate'],
                ),
            )

        return data


@dataclasses.dataclass
class TariffObject:
    name: str
    energy_type: models.EnergyType
    metric_unit: models.MetricUnit
    direction: models.Direction
    valid_from: str | None = None
    valid_until: str | None = None
    currency: str = 'GBP'
    rates: list[RateObject] = dataclasses.field(default_factory=list)

    @property
    def default_rate(self) -> float:
        for rate in self.rates:
            if rate.interval_from == time(hour=2) and rate.interval_end == time(hour=16):
                return rate.unit_rate
        # otherwise we do not know - give the first rate value
        return self.rates[0].unit_rate

    @classmethod
    def from_object(cls, name: str, obj: dict) -> Self:
        energy_str, direction_str, metric_unit_str = obj['unit'].split('_')
        energy_type = models.EnergyType[energy_str.upper()]
        direction = models.Direction[direction_str.upper()]
        metric_unit = models.MetricUnit[metric_unit_str.upper()]
        return cls(
            name=name,
            energy_type=energy_type,
            metric_unit=metric_unit,
            direction=direction,
            valid_from=(datetime.fromisoformat(obj['valid_from']) if 'valid_from' in obj else None),
            valid_until=(datetime.fromisoformat(obj['valid_until']) if 'valid_until' in obj else None),
            currency=obj.get('currency', 'GBP'),
            rates=sorted(RateObject.from_list(obj['rates']), key=attrgetter('interval_from')),
        )


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            'file_path',
            type=str,
            nargs='+',
            help='The path to the JSON config file',
        )

    def _load_tariff(self, tariff_obj: TariffObject):
        with transaction.atomic():
            tariff = models.Tariff.objects.create(
                name=tariff_obj.name,
                energy_type=tariff_obj.energy_type,
                metric_unit=tariff_obj.metric_unit,
                direction=tariff_obj.direction,
                valid_from=tariff_obj.valid_from,
                valid_until=tariff_obj.valid_until,
                currency=tariff_obj.currency,
                default_rate=tariff_obj.default_rate,
            )
            for rate in tariff_obj.rates:
                models.Rate.objects.create(
                    interval_from=rate.interval_from,
                    interval_end=rate.interval_end,
                    unit_rate=rate.unit_rate,
                    tariff=tariff,
                )

    def load_file(self, filename: str):
        self.stdout.write(f'Loading data from {filename}')
        with open(filename, 'r') as fin:
            data = json.load(fin)

        existing_tariffs = set(row['name'] for row in models.Tariff.objects.values('name'))

        for tariff_name, tariff in data['tariffs'].items():
            if tariff_name in existing_tariffs:
                # TODO(tr) option to override?
                self.stdout.write(f'Skipping existing {tariff_name}')
                continue
            self.stdout.write(f'Loading {tariff_name}')

            tariff_obj = TariffObject.from_object(tariff_name, tariff)
            # TODO(tr) check that we have rates for every hours!
            self._load_tariff(tariff_obj)

    def handle(self, file_path: list[str], **kwargs):
        for filepath in file_path:
            try:
                self.load_file(filepath)
            except Exception as ex:
                self.stderr.write(f'Failed to load {filepath}')
                self.stderr.write(f'Error: {ex.__class__.__name__}: {ex}')
                logger.exception(f'For {filepath}')
                continue
