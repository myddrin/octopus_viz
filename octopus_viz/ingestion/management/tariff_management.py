import dataclasses
from datetime import time, datetime, date
from typing import Optional

from django.db import transaction

from ingestion import models
from ingestion.models import EnergyType, MetricUnit


@dataclasses.dataclass
class NewFluxTariff:
    start_date: date
    end_date: date | None
    direction: models.Direction
    low_rate: float
    base_rate: float
    peak_rate: float


def add_new_flux_tariff(params: NewFluxTariff, *, currency: str = 'GBP') -> Optional[str]:
    # TODO(tr) Get currency from settings
    with transaction.atomic():
        direction = models.Direction(params.direction)
        name = f'flux_{direction.label.lower()}_{params.start_date.strftime("%Y-%m-%d")}'
        tariff = models.Tariff(
            name=name,
            energy_type=EnergyType.ELECTRICITY,
            metric_unit=MetricUnit.KWH,
            direction=params.direction,
            valid_from=params.start_date,
            valid_until=params.end_date,
            currency=currency,
            default_rate=params.base_rate,
        )
        tariff.save()

        last_time = time(hour=0)
        for until_time, rate in (
            (time(hour=2), params.base_rate),
            (time(hour=4), params.low_rate),
            (time(hour=16), params.base_rate),
            (time(hour=19), params.peak_rate),
            (time(hour=0), params.base_rate),
        ):
            models.Rate(
                interval_from=last_time,
                interval_end=until_time,
                unit_rate=rate,
                tariff=tariff,
            ).save()
            last_time = until_time

    # TODO(tr) handle integrity errors
    return tariff.name


@dataclasses.dataclass
class FinishCurrentTariff:
    direction: models.Direction
    valid_until: datetime.date


def finish_current_tariff(current_tariff: models.Tariff, params: FinishCurrentTariff) -> Optional[str]:
    with transaction.atomic():
        if current_tariff.valid_until is None:
            current_tariff.valid_until = params.valid_until
            current_tariff.save()
            return current_tariff.name

    return None
