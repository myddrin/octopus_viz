from typing import Sequence, List, Dict, Iterable

from octopus_viz.octopus_client import dto


def aggregate_by_period(
    consumption: Iterable[dto.Consumption],
    *,
    interval_start_fmt: str = '%H:%M',
    tariffs: list[dto.Tariff] = (),
) -> List[dto.ConsumptionPrice]:
    # assumes they are all for the same unit

    cache_by_interval_start: Dict[str, dto.ConsumptionPrice] = {}

    for data_point in consumption:
        key = data_point.interval_start.strftime(interval_start_fmt)
        present = cache_by_interval_start.get(key)

        price, currency = dto.ConsumptionPrice.get_price(data_point, tariffs)
        price_data = dto.ConsumptionPrice(
            data_point,
            price,
            currency,
        )
        if present is None:
            cache_by_interval_start[key] = price_data
        else:
            present += price_data

    return [
        cache_by_interval_start[key]
        for key in sorted(cache_by_interval_start.keys())
    ]
