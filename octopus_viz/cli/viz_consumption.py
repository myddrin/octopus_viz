import argparse
import logging

from plotly import graph_objs as go

from octopus_viz.cli.utils import add_common_aggregate_args
from octopus_viz.octopus_client import dto
from octopus_viz.octopus_client.api import Config, get_consumption_data
from octopus_viz.viz.aggregator import aggregate_by_period


logger = logging.getLogger(__name__)


def make_histogram(
    consumption: list[dto.Consumption],
    aggregate_format: str,
    *,
    config: Config,
) -> go.Bar:

    y = []
    x = []
    for data_point in consumption:
        y.append(data_point.consumption)
        x.append(data_point.interval_start.strftime(aggregate_format))

    return go.Bar(
        name=f'{config.label()} in {config.unit.metric_unit.value}',
        y=y,
        x=x,
    )


def main():
    parser = argparse.ArgumentParser(
        description='Raw access to the consumption of all configured meters.',
    )
    add_common_aggregate_args(parser)
    parser.add_argument(
        '--output', '-o', type=str, default=None,
        help='Write the output as an HTML file',
    )
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    configs = Config.from_json(args.config_filename)

    data = []
    for cfg in configs:
        raw_data = aggregate_by_period(
            get_consumption_data(args.period_from, args.period_to, config=cfg),
            interval_start_fmt=args.aggregate_format,
        )
        data.append(make_histogram(raw_data, args.aggregate_format, config=cfg))

    fig = go.Figure(
        data=data,
        layout_title_text=f'Octopus Viz - Time in UTC using {args.period_from=} {args.period_to=}',
    )
    if args.output is None:
        logger.info(f'Displaying {len(data)} histograms')
        fig.show()  # TODO(tr) does not work with my WSL2 setup
    else:
        logger.info(f'Writing {len(data)} histograms to {args.output}')
        fig.write_html(args.output)
