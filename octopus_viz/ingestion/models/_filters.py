from datetime import datetime

from django.db.models import QuerySet

from ._meter import Meter, MPAN
from ._consumption import Consumption


class MeterFilters:
    def __init__(self, instance: Meter | MPAN):
        self.instance = instance

    def filter_consumptions(self) -> QuerySet:
        if isinstance(self.instance, Meter):
            return Consumption.objects.filter(meter=self.instance)
        elif isinstance(self.instance, MPAN):
            return Consumption.objects.filter(meter__mpan=self.instance)
        else:
            raise RuntimeError(f'Unsupported for {self.instance.__class__.__name__}')

    def get_first_consumption(self) -> datetime | None:
        try:
            latest = self.filter_consumptions().order_by('interval_start')[0]
        except IndexError:
            return None
        else:
            return latest.earliest

    def get_latest_consumption(self) -> datetime | None:
        try:
            latest = self.filter_consumptions().order_by('-interval_end')[0]
        except IndexError:
            return None
        else:
            return latest.latest
