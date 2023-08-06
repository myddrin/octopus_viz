import dataclasses
import json
import logging
import os
from typing import (
    ClassVar,
    Iterable,
)

from octopus_viz.octopus_client import (
    api,
    dto,
)


logger = logging.getLogger(__name__)


@dataclasses.dataclass
class DumbCacheParam:
    period_from: str
    period_to: str
    meter: dto.Meter

    @property
    def cache_filename(self) -> str:
        return os.path.join(
            DumbCache.cache_dir,
            f'{self.meter.serial}_{self.meter.meter_id}_{self.period_from}_{self.period_to}.json',
        )


class DumbCache:
    """Save past requests to a file and reload them if they are present."""
    cache_dir: ClassVar[str] = 'octopus_cache'

    def __init__(self):
        if not os.path.isdir(self.cache_dir):
            os.mkdir(self.cache_dir)

    def _load_dumb_cache(self, req: DumbCacheParam) -> Iterable[dto.Consumption]:
        with open(req.cache_filename, 'r') as fin:
            for line in fin:
                data = json.loads(line)
                yield dto.Consumption.from_json_response(data, req.meter.unit)

    def _write_dumb_cache(self, req: DumbCacheParam, consumption):
        with open(req.cache_filename, 'a') as fout:
            data = dataclasses.asdict(consumption)
            data['interval_start'] = consumption.interval_start.isoformat()
            data['interval_end'] = consumption.interval_end.isoformat()
            data['unit'] = consumption.unit.value
            json.dump(data, fp=fout)
            fout.write('\n')  # one bit of JSON per line

    def has_data(self, req: DumbCacheParam) -> bool:
        return os.path.isfile(req.cache_filename)

    def get_consumption_data(
        self,
        period_from: str = None,
        period_to: str = None,
        *,
        meter: dto.Meter,
    ) -> Iterable[dto.Consumption]:
        req = DumbCacheParam(period_from, period_to, meter=meter)
        if self.has_data(req):
            logger.info(f'Loading from {req.cache_filename}')
            yield from self._load_dumb_cache(req)
        else:
            logger.info(f'Writing to {req.cache_filename}')
            for consumption in api.get_consumption_data(period_from, period_to, meter=meter):
                self._write_dumb_cache(req, consumption)
                yield consumption
