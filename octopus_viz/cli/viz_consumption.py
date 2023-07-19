import argparse
import logging
from typing import Callable

from plotly import graph_objs as go

from octopus_viz.cli.utils import add_common_aggregate_args, label_by_period_gen, \
    label_by_tariff_gen
from octopus_viz.octopus_client import dto
from octopus_viz.octopus_client.api import get_consumption_data
from octopus_viz.octopus_client.dto import Meter
from octopus_viz.viz.aggregator import aggregate_by_period, aggregate_by_tariff

logger = logging.getLogger(__name__)


def make_usage_histogram(
    conso_prices: list[dto.ConsumptionPrice],
    *,
    label_gen: Callable[[dto.ConsumptionPrice], str],
    meter: Meter,
    show_price: bool = False,
) -> go.Bar:

    price = []
    consumption = []
    custom = []
    when = []
    if meter.unit.direction == dto.Direction.importing:
        label = 'consumption'
    elif meter.unit.direction == dto.Direction.exporting:
        label = 'generation'
    else:
        raise ValueError(f'Unexpected {meter.unit.direction}')

    if not conso_prices:
        start_period = None
        end_period = None
        currency = None
    else:
        start_period = conso_prices[0].consumption.interval_start
        end_period = conso_prices[0].consumption.interval_end
        currency = conso_prices[0].currency

    for data_point in conso_prices:
        price.append(data_point.price)
        consumption.append(data_point.consumption.consumption)
        when.append(label_gen(data_point))
        custom.append({
            'consumption': data_point.consumption.consumption,
            'unit': data_point.consumption.unit.metric_unit.value,
            'price': data_point.price,
            'currency': data_point.currency,
            'earliest': data_point.consumption.interval_start,
            'latest': data_point.consumption.interval_end,
        })
        start_period = min(start_period, data_point.consumption.interval_start)
        end_period = max(end_period, data_point.consumption.interval_end)

    if show_price:
        selected_unit = currency
        data = price
    else:
        selected_unit = meter.unit.metric_unit.value
        data = consumption

    return go.Bar(
        name=(
            f'{meter.label()} in {selected_unit}<br>'
            f'total: {sum(consumption):0.2f} {meter.unit.metric_unit.value}, {sum(price):0.2f} {currency}<br>'
            f'period: {start_period.date()} and {end_period.date()}'
        ),
        y=data,
        x=when,
        customdata=custom,
        hovertemplate=(
            f'%{{x}}: %{{customdata.consumption:0.2f}} %{{customdata.unit}}<br>'
            f'{label}: %{{customdata.price:0.2f}} %{{customdata.currency}}<br>'
            f'period: %{{customdata.earliest:%Y-%m-%d}} to %{{customdata.latest:%Y-%m-%d}}'
        ),
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
    parser.add_argument(
        '--show-prices', action='store_true',
        help='Show prices as default view instead of consumption',
    )
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    config = dto.Config.from_json(args.config_filename)

    data = []
    for meter in config.meters:
        raw_data = get_consumption_data(args.period_from, args.period_to, meter=meter)
        if not args.aggregate_by_tariff:
            label_gen = label_by_period_gen(args.aggregate_period_format)
            agg_data = aggregate_by_period(
                raw_data,
                label_gen=label_gen,
                tariffs=config.tariffs.get(meter.unit, []),
            )
            data.append(make_usage_histogram(
                agg_data,
                label_gen=label_by_period_gen(args.aggregate_period_format),
                meter=meter,
                show_price=args.show_prices,
            ))
        else:
            agg_data = aggregate_by_tariff(raw_data, tariffs=config.tariffs.get(meter.unit, []))
            data.append(make_usage_histogram(
                agg_data,
                label_gen=label_by_tariff_gen(tariffs=config.all_tariffs),
                meter=meter,
                show_price=args.show_prices,
            ))

    fig = go.Figure(
        data=data,
        layout_title_text=(
            f'Octopus Viz - Time in UTC using {args.period_from=} {args.period_to=}'
        ),
    )
    if args.output is None:
        logger.info(f'Displaying {len(data)} histograms')
        fig.show()  # TODO(tr) does not work with my WSL2 setup
    else:
        logger.info(f'Writing {len(data)} histograms to {args.output}')
        fig.write_html(args.output)
