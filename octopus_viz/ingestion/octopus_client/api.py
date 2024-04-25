import logging
from datetime import datetime

import pytz
import requests
from requests.auth import HTTPBasicAuth

from ingestion import models


logger = logging.getLogger(__name__)


class OctopusAPI:
    OCTOPUS_API_V1 = 'https://api.octopus.energy/v1'

    @classmethod
    def build_consumption_endpoint(cls, meter: models.Meter) -> str:
        if meter.energy_type == models.EnergyType.ELECTRICITY:
            # TODO(tr) use urllib?
            return f'{cls.OCTOPUS_API_V1}/electricity-meter-points/{meter.mpan.mpan}/meters/{meter.serial}/consumption'
        elif meter.energy_type == models.EnergyType.GAS:
            return f'{cls.OCTOPUS_API_V1}/gas-meter-points/{meter.mpan.mpan}/meters/{meter.serial}/consumption'
        else:
            raise NotImplementedError(f'Unexpected config {meter}')

    @classmethod
    def handle_datetime(cls, data: dict, field: str) -> datetime:
        """Extract a tz aware datetime from data and return it as a UTC datetime"""
        octopus_datetime = datetime.fromisoformat(data.pop(field))
        if octopus_datetime.tzinfo is None:
            raise ValueError(f'Unexpected tz unaware {field} from octopus')
        return octopus_datetime.astimezone(pytz.UTC)

    def __init__(self, meter: models.Meter):
        self.meter = meter
        self.session = requests.Session()
        self.session.auth = HTTPBasicAuth(self.meter.api_key, '')
        self.consumption_endpoint = self.build_consumption_endpoint(self.meter)

    def build_consumption_from_json(self, data: dict) -> models.Consumption:
        interval_start = self.handle_datetime(data, 'interval_start')
        interval_end = self.handle_datetime(data, 'interval_end')
        consumption = float(data.pop('consumption'))
        # TODO(tr) warning for unexpected fields?

        obj = models.Consumption.objects.create(
            consumption=consumption,
            interval_start=interval_start,
            interval_end=interval_end,
            meter=self.meter,
        )
        return obj

    def get_consumption_data(
        self,
        period_from: datetime = None,
        period_to: datetime = None,
    ) -> int:
        if period_to is not None and period_from is None:
            raise ValueError('period_from has to be specified when using period_to')

        params = {}
        if period_from:
            params['period_from'] = period_from.isoformat()
        if period_to:
            params['period_to'] = period_to.isoformat()

        req = requests.PreparedRequest()
        req.prepare_url(self.consumption_endpoint, params)
        endpoint = req.url

        logger.info(f'Getting data for {self.meter.serial=} for {period_from=} {period_to=}')
        pages = 0
        loaded = 0
        while endpoint is not None:
            response = self.session.get(endpoint)
            response.raise_for_status()

            data = response.json()

            # For most cases this could be a list,
            # but we may want to support pagination in the future
            for result in data['results']:
                consumption = self.build_consumption_from_json(result)
                consumption.update_rate()
                loaded += 1

            endpoint = data.get('next')
            pages += 1

        logger.info(f'Gathered {pages} pages of data for {self.meter.serial=} for {period_from=} {period_to=}')
        return loaded
