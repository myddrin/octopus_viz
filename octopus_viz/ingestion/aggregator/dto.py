import dataclasses
import datetime
from typing import Self


@dataclasses.dataclass
class ConsumptionPrice:
    consumption: float
    metric_unit: str
    earliest: datetime.datetime
    latest: datetime.datetime
    price: float | None
    currency: str | None

    def __add__(self, other: Self):
        if not isinstance(other, self.__class__):
            raise ValueError()
        if self.currency != other.currency and not (self.currency is None or other.currency is None):
            raise ValueError(f'Cannot add two different currencies together: {self.currency} and {other.currency}')
        if self.metric_unit != other.metric_unit:
            raise ValueError(f'Cannot add different units: {self.metric_unit} and {other.metric_unit}')

        self.consumption += other.consumption
        self.earliest = min(self.earliest, other.earliest)
        self.latest = max(self.latest, other.latest)

        if other.price is not None:
            self.price += other.price
        if self.currency is None:
            self.currency = other.currency

    def as_dict(self) -> dict:
        return dataclasses.asdict(self)
