from datetime import date, timedelta, datetime
from typing import Optional

import pytest

from octopus_viz.octopus_client import dto


def make_flux_tariff(
    name: str,
    unit: dto.ConsumptionUnit,
    *,
    valid_from: date,
    valid_until: Optional[date],
    flux: float,
    day: float,
    peak: float,
) -> dto.Tariff:
    return dto.Tariff(
        name,
        unit,
        currency='GBP',
        valid_from=valid_from,
        valid_until=valid_until,
        rates=[
            dto.PeriodRate(timedelta(hours=0), timedelta(hours=2), rate=day, currency='GBP'),
            dto.PeriodRate(timedelta(hours=2), timedelta(hours=5), rate=flux, currency='GBP'),
            dto.PeriodRate(timedelta(hours=5), timedelta(hours=16), rate=day, currency='GBP'),
            dto.PeriodRate(timedelta(hours=16), timedelta(hours=19), rate=peak, currency='GBP'),
            dto.PeriodRate(timedelta(hours=19), timedelta(hours=24), rate=day, currency='GBP'),
        ],
    )


@pytest.fixture(scope='session')
def flux_exp_tariffs() -> list[dto.Tariff]:
    return [
        make_flux_tariff(
            'flux_export_2023-02',
            dto.ConsumptionUnit.electricity_exporting_kwh,
            valid_from=date(2023, 2, 1),
            valid_until=date(2023, 7, 1),
            day=0.22982,
            flux=0.09389,
            peak=0.36575,
        ),
        make_flux_tariff(
            'flux_export_2023-02',
            dto.ConsumptionUnit.electricity_exporting_kwh,
            valid_from=date(2023, 7, 1),
            valid_until=None,
            day=0.1972,
            flux=0.07432,
            peak=0.32008,
        ),
    ]


@pytest.fixture(scope='session')
def flux_imp_tariffs() -> list[dto.Tariff]:
    return [
        make_flux_tariff(
            'flux_import_2023-07',
            dto.ConsumptionUnit.electricity_importing_kwh,
            valid_from=date(2023, 7, 1),
            valid_until=None,
            day=0.30720,
            flux=0.18432,
            peak=0.43008,
        ),
        make_flux_tariff(
            'flux_import_2023-02',
            dto.ConsumptionUnit.electricity_importing_kwh,
            valid_from=date(2023, 2, 1),
            valid_until=date(2023, 7, 1),
            day=0.33982,
            flux=0.20389,
            peak=0.47575,
        ),
    ]


class TestConsumptionPrice:

    @pytest.mark.parametrize('when, exp_tariff_name', (
        (datetime(2023, 7, 1, 0, 30), 'flux_import_2023-07'),
        (datetime(2023, 7, 1, 0, 0), 'flux_import_2023-07'),
        (datetime(2023, 6, 30, 23, 30), 'flux_import_2023-02'),
        (datetime(2023, 3, 1, 0, 0), 'flux_import_2023-02'),
        (datetime(2023, 2, 1, 0, 0), 'flux_import_2023-02'),
        (datetime(2023, 1, 31, 23, 30), None),
    ))
    def test_get_tariff(
        self,
        flux_imp_tariffs: list[dto.Tariff],
        when: datetime,
        exp_tariff_name: Optional[str],
    ):
        consumption = dto.Consumption(
            consumption=1.23,
            unit=dto.ConsumptionUnit.electricity_importing_kwh,
            interval_start=when,
            interval_end=when + timedelta(minutes=30),
        )
        tariff = dto.ConsumptionPrice.get_tariff(consumption, flux_imp_tariffs)
        if exp_tariff_name is not None:
            assert tariff is not None and tariff.name == exp_tariff_name
        else:
            assert tariff is None
