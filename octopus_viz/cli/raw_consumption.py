import argparse
import logging
from operator import attrgetter
from typing import Iterable

from octopus_viz.cli.utils import add_common_aggregate_args
from octopus_viz.octopus_client import dto
from octopus_viz.octopus_client.api import get_consumption_data
from octopus_viz.octopus_client.dto import Meter
from octopus_viz.viz.aggregator import aggregate_by_period


def console_lines(
    conso_prices: list[dto.ConsumptionPrice],
    aggregate_format: str,
    *,
    meter: Meter,
    top_n: int = 5,
    bottom_n: int = 5,
) -> Iterable[str]:
    start_period = min(conso_prices, key=attrgetter('consumption.interval_start')).consumption.interval_start
    end_period = max(conso_prices, key=attrgetter('consumption.interval_end')).consumption.interval_end

    ordered_consumption = sorted(conso_prices, key=attrgetter('consumption.consumption'))
    top_consumption = {
        f'{data_point.consumption.consumption:0.3f}'
        for data_point in ordered_consumption[-top_n:]
    }
    bottom_consumption = {
        f'{data_point.consumption.consumption:0.3f}'
        for data_point in ordered_consumption[:bottom_n]
    }
    if meter.unit.direction == dto.Direction.importing:
        label = 'consumption'
    elif meter.unit.direction == dto.Direction.exporting:
        label = 'generation'
    else:
        raise ValueError(f'Unexpected {meter.unit.direction}')

    yield f'{label.title()} for {meter.label()} {start_period} <= UTC < {end_period}'
    yield f'{top_consumption=}'
    yield f'{bottom_consumption=}'
    total_kwh = 0.0
    total_money = 0.0
    currency = None
    for data_point in conso_prices:
        when: str = data_point.consumption.interval_start.strftime(aggregate_format)
        conso_str = f'{data_point.consumption.consumption:0.3f}'
        notes = ''
        if conso_str in top_consumption:
            notes = f' <= HIGH {label.upper()}'
        elif conso_str in bottom_consumption:
            notes = f' <= LOW {label.upper()}'

        if data_point.price:
            price_info = f' {data_point.price:0.2f} {data_point.currency}'
        else:
            price_info = ''

        yield f'{when}: {conso_str}{data_point.consumption.unit.metric_unit.value}{price_info}{notes}'
        total_kwh += data_point.consumption.consumption
        total_money += data_point.price
        if currency is None:
            currency = data_point.currency

    if currency is not None:
        currency_info = f'{total_money:0.2f} {currency}'
    else:
        currency_info = ''

    yield (
        f'Total {label} for {meter.label()} '
        f'{start_period} <= UTC < {end_period} '
        f'is {total_kwh:0.3f}{meter.unit.metric_unit.value} '
        f'{currency_info}'
    )


def main():
    parser = argparse.ArgumentParser(
        description='Raw access to the consumption of all configured meters.',
    )
    add_common_aggregate_args(parser)
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    config = dto.Config.from_json(args.config_filename)

    for meter in config.meters:
        raw_data = get_consumption_data(args.period_from, args.period_to, meter=meter)
        data = aggregate_by_period(
            raw_data,
            interval_start_fmt=args.aggregate_format,
            tariffs=config.tariffs.get(meter.unit, []),
        )

        for line in console_lines(data, args.aggregate_format, meter=meter):
            print(line)


if __name__ == '__main__':
    main()
