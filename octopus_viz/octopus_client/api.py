import dataclasses
import json
import logging
from typing import Dict, Generator, Optional

import requests
from requests.auth import HTTPBasicAuth

from octopus_viz.octopus_client import dto


OCTOPUS_API_V1 = 'https://api.octopus.energy/v1'


logger = logging.getLogger(__name__)


@dataclasses.dataclass(frozen=True)
class Config:
    api_key: str
    meter_id: str
    serial: str
    unit: dto.ConsumptionUnit
    alias: str = None

    @property
    def mpan(self) -> Optional[str]:
        """Meter Point Administration Number for electric meters"""
        if self.unit.energy_type == dto.EnergyType.electricity:
            return self.meter_id

    @property
    def mprn(self) -> Optional[str]:
        """Meter Point Reference Number for Gas meters"""
        if self.unit.energy_type == dto.EnergyType.gas:
            return self.meter_id

    def consumption_endpoint(self) -> str:
        if self.unit.energy_type == dto.EnergyType.electricity:
            # TODO(tr) use urllib?
            return f'{OCTOPUS_API_V1}/electricity-meter-points/{self.mpan}/meters/{self.serial}/consumption'
        elif self.unit.energy_type == dto.EnergyType.gas:
            return f'{OCTOPUS_API_V1}/gas-meter-points/{self.mprn}/meters/{self.serial}/consumption'
        else:
            raise NotImplementedError(f'Unexpected config {self}')

    def label(self) -> str:
        if self.alias:
            return self.alias
        return f'Meter {self.serial} ({self.unit.direction.value} {self.unit.energy_type.value})'

    @classmethod
    def from_dict(cls, data: dict) -> 'Config':
        unit = dto.ConsumptionUnit(data.pop('unit'))  # transform to enum
        data['unit'] = unit
        if 'meter_id' not in data:
            if unit.energy_type == dto.EnergyType.electricity:
                data['meter_id'] = data.pop('mpan')
            elif unit.energy_type == dto.EnergyType.gas:
                data['meter_id'] = data.pop('mprn')
            else:
                raise ValueError(f'Unexpected type of meter')
        return cls(**data)

    @classmethod
    def from_json(cls, filename: str) -> list['Config']:
        logger.info(f'Loading configuration from "{filename}"')
        with open(filename, 'r') as config_input:
            data: Dict = json.load(config_input)

        base_kwargs = {
            k: v
            for k, v in data.items()
            if k != 'meters'
        }
        meter_configs = [
            cls.from_dict(base_kwargs | meter_kwargs)
            for meter_kwargs in data['meters']
        ]
        logger.info(f'Loaded {len(meter_configs)} from {filename}')
        return meter_configs


def get_consumption_data(
    period_from: str = None,
    period_to: str = None,
    *,
    config: Config,
) -> Generator[dto.Consumption, None, None]:
    if (
        period_from is None and period_to is not None
    ) or (
        period_from is not None and period_to is None
    ):
        raise ValueError('Both period_from and period_to have to be specified')

    endpoint = config.consumption_endpoint()

    session = requests.Session()
    session.auth = HTTPBasicAuth(config.api_key, '')

    logger.info(f'Getting data for {config.serial=} for {period_from=} {period_to=}')
    pages = 0
    while endpoint is not None:
        response = session.get(endpoint)
        response.raise_for_status()

        data = response.json()

        # For most cases this could be a list, but we may want to support pagination in the future
        for result in data['results']:
            yield dto.Consumption.from_json_response(result, unit=config.unit)

        endpoint = data.get('next')
        pages += 1

    logger.info(f'Gathered {pages} pages of data for {config.serial=} for  {period_from=} {period_to=}')
