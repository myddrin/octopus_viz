import logging
from datetime import datetime
from typing import Iterable

import requests
from django.db import IntegrityError, transaction
from requests.auth import HTTPBasicAuth

from ingestion import models


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
        """Extract a tz aware datetime from data"""
        octopus_datetime = datetime.fromisoformat(data.pop(field))
        if octopus_datetime.tzinfo is None:
            raise ValueError(f'Unexpected tz unaware {field} from octopus')
        return octopus_datetime

    def __init__(self, meter: models.Meter, *, logger: logging.Logger | None = None, update_existing: bool = True):
        self.meter = meter
        self.session = requests.Session()
        self.session.auth = HTTPBasicAuth(self.meter.api_key, '')
        self.consumption_endpoint = self.build_consumption_endpoint(self.meter)
        if logger is None:
            logger = logging.getLogger(__name__)
        self.logger = logger
        self.update_existing = update_existing

    def build_consumption_from_json(self, data: dict) -> models.Consumption:
        self.logger.debug(f'Building row from {data=}')
        interval_start = self.handle_datetime(data, 'interval_start')
        interval_end = self.handle_datetime(data, 'interval_end')
        consumption = float(data.pop('consumption'))
        # TODO(tr) warning for unexpected fields?

        try:
            with transaction.atomic():
                return models.Consumption.objects.create(
                    consumption=consumption,
                    interval_start=interval_start,
                    interval_end=interval_end,
                    meter=self.meter,
                )
        except IntegrityError:
            if not self.update_existing:
                raise
            existing_row = models.Consumption.objects.filter(
                interval_start=interval_start,
                interval_end=interval_end,
                meter=self.meter,
            ).first()
            self.logger.debug(f'  Updating {existing_row} from {existing_row.consumption}->{consumption}')
            existing_row.consumption = consumption
            existing_row.save()
            return existing_row

    def get_consumption_data(
        self,
        period_from: datetime = None,
        period_to: datetime = None,
    ) -> Iterable[dict]:
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

        self.logger.info(
            f'Getting data for {self.meter} for period_from={params.get("period_from")} period_to={params.get("period_to")}',
        )
        pages = 0
        while endpoint is not None:
            response = self.session.get(endpoint)
            self.logger.debug(f'< Got {response.status_code} from {response.url}')
            response.raise_for_status()

            data = response.json()

            # For most cases this could be a list,
            # but we may want to support pagination in the future
            for result in data['results']:
                yield result
                # consumption.update_rate()

            endpoint = data.get('next')
            pages += 1

        self.logger.info(f'Gathered {pages} pages of data for {self.meter.serial=} for {period_from=} {period_to=}')
