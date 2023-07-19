from typing import List, Dict, Iterable, Callable

from octopus_viz.octopus_client import dto


def aggregate_by_period(
    consumption: Iterable[dto.Consumption],
    *,
    label_gen: Callable[[dto.ConsumptionPrice], str],
    tariffs: list[dto.Tariff] = (),
) -> List[dto.ConsumptionPrice]:
    # assumes they are all for the same unit

    cache_by_interval_start: Dict[str, dto.ConsumptionPrice] = {}

    for data_point in consumption:
        price, currency = dto.ConsumptionPrice.get_price(data_point, tariffs)
        price_data = dto.ConsumptionPrice(
            data_point,
            price,
            currency,
        )

        key = label_gen(price_data)
        present = cache_by_interval_start.get(key)
        if present is None:
            cache_by_interval_start[key] = price_data
        else:
            present += price_data

    return [
        cache_by_interval_start[key]
        for key in sorted(cache_by_interval_start.keys())
    ]


def aggregate_by_tariff(
    consumption: Iterable[dto.Consumption],
    *,
    tariffs: list[dto.Tariff]
) -> list[dto.ConsumptionPrice]:
    by_rate: dict[str, dto.ConsumptionPrice] = {}

    for data_point in consumption:
        rates = dto.ConsumptionPrice.get_period_rates(data_point, tariffs)
        if len(rates) > 1:
            raise ValueError(f'Could not find single rate for {data_point}')
        elif not rates:
            raise ValueError(f'Could not find any rate for {data_point}')
        # otherwise we have a single rate for that period
        rate = rates[0]
        rate_key = f'{rate.rate:0.3f}'  # float are not reliable hashes
        price_data = dto.ConsumptionPrice(
            data_point,
            rate.rate * data_point.consumption,
            rate.currency,
        )
        present = by_rate.get(rate_key)
        if present is None:
            by_rate[rate_key] = price_data
        else:
            present += price_data

    return [
        by_rate[key]
        for key in sorted(by_rate.keys())
    ]
