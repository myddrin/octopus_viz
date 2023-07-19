import argparse
from datetime import datetime, timedelta
from typing import Callable

from octopus_viz.octopus_client import dto

today = datetime.utcnow()


def add_common_aggregate_args(parser: argparse.ArgumentParser):
    parser.add_argument(
        '--period-from', type=str, default=None,
        help='Period start (inclusive). Need to specify --period-to',
    )
    parser.add_argument(
        '--period-to', type=str, default=None,
        help='Period end (exclusive). Need to specify --period-from',
    )
    parser.add_argument(
        '--aggregate-period-format', type=str, default='%H:%M',
        help=(
            'A strftime format to use for the aggregation of the data. '
            'Default is "%(default)s" which means by half-hour period'
        ),
    )
    parser.add_argument(
        '--aggregate-by-tariff', action='store_true',
        help='Instead of aggregating by period, aggregate by tariff price.',
    )
    parser.add_argument(
        'config_filename', type=str,
        help='Path to the configuration file',
    )
    parser.add_argument(
        '--verbose', '-v', action='store_true',
    )


def label_by_period_gen(aggregate_format: str) -> Callable[[dto.ConsumptionPrice], str]:
    def _gen(consumption: dto.ConsumptionPrice) -> str:
        return consumption.consumption.interval_start.strftime(aggregate_format)
    return _gen


def label_by_tariff_gen(tariffs: list[dto.Tariff]) -> Callable[[dto.ConsumptionPrice], str]:
    def _gen(consumption: dto.ConsumptionPrice) -> str:
        # TODO(tr) Make a tariff alias?
        import_tariffs = []
        export_tariffs = []
        for tariff in tariffs:
            if tariff.unit.direction == dto.Direction.importing:
                import_tariffs.append(tariff)
            else:
                export_tariffs.append(tariff)

        try:
            import_rate = dto.ConsumptionPrice.get_rate(consumption.consumption, import_tariffs)
            export_rate = dto.ConsumptionPrice.get_rate(consumption.consumption, export_tariffs)
        except:
            return f'{consumption.price / consumption.consumption.consumption:0.3f} {consumption.currency}'
        else:
            if import_rate.interval_start != export_rate.interval_start:
                raise ValueError('Unexpected different periods for importing/exporting tariffs')

            if import_rate.interval_start == timedelta(hours=2):
                name = 'flux'
            elif import_rate.interval_start == timedelta(hours=16):
                name = 'peak'
            elif import_rate.interval_start in (timedelta(hours=0), timedelta(hours=19)):
                name = 'day'
            else:
                name = 'unknown-flux'

            return f'{name} (import: {import_rate.rate:0.3f}, export {export_rate.rate:0.3f} {import_rate.currency})'

    return _gen


def label_by_rate(consumption: dto.ConsumptionPrice) -> str:
    # TODO(tr) Rate is lost from consumption price... maybe accumulate in a list?
    return f'{consumption.price / consumption.consumption.consumption:0.3f} {consumption.currency}'
