import argparse
import logging
from operator import attrgetter
from typing import Optional, Iterable

from octopus_viz.octopus_client import dto
from octopus_viz.octopus_client.api import Config, get_consumption_data
from octopus_viz.viz.aggregator import aggregate_by_period


def console_lines(
    consumption: list[dto.Consumption],
    aggregate_format: str,
    *,
    config: Config,
    top_n: int = 5,
    bottom_n: int = 5,
) -> Iterable[str]:
    start_period = min(consumption, key=attrgetter('interval_start')).interval_start
    end_period = max(consumption, key=attrgetter('interval_end')).interval_end

    ordered_consumption = sorted(consumption, key=attrgetter('consumption'))
    top_consumption = {
        f'{data_point.consumption:0.3f}'
        for data_point in ordered_consumption[-top_n:]
    }
    bottom_consumption = {
        f'{data_point.consumption:0.3f}'
        for data_point in ordered_consumption[:bottom_n]
    }
    if config.unit.direction == dto.Direction.importing:
        label = 'consumption'
    elif config.unit.direction == dto.Direction.exporting:
        label = 'generation'
    else:
        raise ValueError(f'Unexpected {config.unit.direction}')

    yield f'{label.title()} for {config.label()} {start_period} <= UTC < {end_period}'
    yield f'{top_consumption=}'
    yield f'{bottom_consumption=}'
    total = 0.0
    for data_point in consumption:
        when: str = data_point.interval_start.strftime(aggregate_format)
        conso_str = f'{data_point.consumption:0.3f}'
        notes = ''
        if conso_str in top_consumption:
            notes = f' <= HIGH {label.upper()}'
        elif conso_str in bottom_consumption:
            notes = f' <= LOW {label.upper()}'

        yield f'{when}: {conso_str}{data_point.unit.metric_unit.value}{notes}'
        total += data_point.consumption

    yield (
        f'Total {label} for {config.label()} '
        f'{start_period} <= UTC < {end_period} '
        f'is {total:0.3f}{config.unit.metric_unit.value}'
    )


def main():
    parser = argparse.ArgumentParser(
        description='Raw access to the consumption of all configured meters.',
    )
    parser.add_argument(
        '--period-from', type=str, default=None,
        help='Period start (inclusive). Need to specify --period-to',
    )
    parser.add_argument(
        '--period-to', type=str, default=None,
        help='Period end (exclusive). Need to specify --period-from',
    )
    parser.add_argument(
        '--aggregate-format', type=str, default='%H:%M',
        help='A strftime format to use for the aggregation of the data. Default is %(default)s=by period',
    )
    parser.add_argument(
        'config_filename', type=str,
        help='Path to the configuration file',
    )
    parser.add_argument(
        '--verbose', '-v', action='store_true',
    )
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    configs = Config.from_json(args.config_filename)

    for cfg in configs:
        raw_data = aggregate_by_period(
            get_consumption_data(args.period_from, args.period_to, config=cfg),
            interval_start_fmt=args.aggregate_format,
        )

        for line in console_lines(raw_data, args.aggregate_format, config=cfg):
            print(line)
