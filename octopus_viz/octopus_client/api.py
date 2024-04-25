from typing import Generator

import requests
from requests.auth import HTTPBasicAuth

from octopus_viz.octopus_client import dto, logger


def get_consumption_data(
    period_from: str = None,
    period_to: str = None,
    *,
    meter: dto.Meter,
) -> Generator[dto.Consumption, None, None]:
    if period_to is not None and period_from is None:
        raise ValueError("period_from has to be specified when using period_to")

    params = {}
    if period_from:
        params["period_from"] = period_from
    if period_to:
        params["period_to"] = period_to
    req = requests.PreparedRequest()
    req.prepare_url(meter.consumption_endpoint(), params)
    endpoint = req.url

    session = requests.Session()
    session.auth = HTTPBasicAuth(meter.api_key, "")

    logger.info(f"Getting data for {meter.serial=} for {period_from=} {period_to=}")
    pages = 0
    while endpoint is not None:
        response = session.get(endpoint)
        response.raise_for_status()

        data = response.json()

        # For most cases this could be a list, but we may want to support pagination in the future
        for result in data["results"]:
            yield dto.Consumption.from_json_response(result, unit=meter.unit)

        endpoint = data.get("next")
        pages += 1

    logger.info(
        f"Gathered {pages} pages of data for {meter.serial=} for {period_from=} {period_to=}"
    )
