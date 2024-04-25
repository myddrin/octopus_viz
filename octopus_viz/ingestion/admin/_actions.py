from ingestion.models import Consumption, Meter


class UpdateRates:
    """
    Update all rates for a meter based on the related Tariff and Rates
    """

    def __init__(self, consumption: Consumption):
        self.consumption = consumption


class DownloadData:
    """
    Download data from the octopus energy API
    """

    def __init__(self, meter: Meter):
        self.meter = meter
