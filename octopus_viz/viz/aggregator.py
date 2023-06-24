from typing import Sequence, List, Dict, Iterable

from octopus_viz.octopus_client import dto


def aggregate_by_period(
    consumption: Iterable[dto.Consumption],
    *,
    interval_start_fmt ='%H:%M',
) -> List[dto.Consumption]:
    # assumes they are all for the same unit

    cache_by_interval_start: Dict[str, dto.Consumption] = {}

    for data_point in consumption:
        key = data_point.interval_start.strftime(interval_start_fmt)
        present = cache_by_interval_start.get(key)
        if present is None:
            cache_by_interval_start[key] = data_point
        else:
            cache_by_interval_start[key] = present.aggregate(data_point)

    return [
        cache_by_interval_start[key]
        for key in sorted(cache_by_interval_start.keys())
    ]
