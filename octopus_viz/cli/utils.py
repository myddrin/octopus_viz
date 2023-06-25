import argparse
from datetime import datetime


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
        '--aggregate-format', type=str, default='%H:%M',
        help=(
            'A strftime format to use for the aggregation of the data. '
            'Default is "%(default)s" which means by half-hour period'
        ),
    )
    parser.add_argument(
        'config_filename', type=str,
        help='Path to the configuration file',
    )
    parser.add_argument(
        '--verbose', '-v', action='store_true',
    )
