import dataclasses
import json
import os
import sys
from typing import Iterable

import requests
from requests.auth import HTTPBasicAuth

from octopus_viz.octopus_client import dto, logger

_use_dumb_cache = True
_cache_dir = 'octopus_cache'


def _write_dumb_cache(consumption: dto.Consumption, filename: str):
    with open(filename, 'a') as fout:
        data = dataclasses.asdict(consumption)
        data['interval_start'] = consumption.interval_start.isoformat()
        data['interval_end'] = consumption.interval_end.isoformat()
        data['unit'] = consumption.unit.value
        json.dump(data, fp=fout)
        fout.write('\n')  # one bit of JSON per line


def _load_dumb_cache(filename: str, meter_unit: dto.ConsumptionUnit) -> Iterable[dto.Consumption]:
    with open(filename, 'r') as fin:
        for line in fin:
            data = json.loads(line)
            yield dto.Consumption.from_json_response(data, meter_unit)


def get_consumption_data(
    period_from: str = None,
    period_to: str = None,
    *,
    meter: dto.Meter,
) -> Iterable[dto.Consumption]:
    if period_to is not None and period_from is None:
        raise ValueError('period_from has to be specified when using period_to')

    if _use_dumb_cache and not os.path.isdir(_cache_dir):
        os.mkdir(_cache_dir)

    cache_filename = f'{_cache_dir}/{meter.serial}_{meter.meter_id}_{period_from}_{period_to}.json'
    if _use_dumb_cache:
        if os.path.isfile(cache_filename):
            logger.info(f'Loading from {cache_filename}')
            yield from _load_dumb_cache(cache_filename, meter.unit)
        else:
            logger.info(f'Writing to {cache_filename}')

    params = {}
    if period_from:
        params['period_from'] = period_from
    if period_to:
        params['period_to'] = period_to
    req = requests.PreparedRequest()
    req.prepare_url(meter.consumption_endpoint(), params)
    endpoint = req.url

    session = requests.Session()
    session.auth = HTTPBasicAuth(meter.api_key, '')

    logger.info(f'Getting data for {meter.serial=} for {period_from=} {period_to=}')
    pages = 0
    while endpoint is not None:
        response = session.get(endpoint)
        response.raise_for_status()

        data = response.json()

        # For most cases this could be a list, but we may want to support pagination in the future
        for result in data['results']:
            obj = dto.Consumption.from_json_response(result, unit=meter.unit)
            if _use_dumb_cache:
                _write_dumb_cache(obj, cache_filename)
            yield obj

        endpoint = data.get('next')
        pages += 1

    logger.info(f'Gathered {pages} pages of data for {meter.serial=} for {period_from=} {period_to=}')
