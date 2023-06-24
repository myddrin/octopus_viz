import dataclasses
import datetime
import enum
from typing import Tuple


from octopus_viz.octopus_client.utils import handle_datetime


class EnergyType(enum.Enum):
    electricity = 'electricity'
    gas = 'gas'


class Direction(enum.Enum):
    importing = 'importing'  # because import is a keyword
    exporting = 'exporting'


class MetricUnit(enum.Enum):
    kwh = 'kWh'
    m3 = 'm3'


class ConsumptionUnit(enum.Enum):
    """
    A compound enum of the {EnergyType}_{Direction}_{MetricUnit}
    Not part of Octopus API
    """
    electricity_importing_kwh = 'electricity_importing_kwh'
    electricity_exporting_kwh = 'electricity_exporting_kwh'
    gas_importing_kwh = 'gas_importing_kwh'
    gas_importing_m3 = 'gas_importing_m3'

    def _parts(self) -> Tuple[str, str, str]:
        energy, direction, unit = self.name.split('_')
        return energy, direction, unit

    @property
    def energy_type(self) -> EnergyType:
        return getattr(EnergyType, self._parts()[0])

    @property
    def direction(self) -> Direction:
        return getattr(Direction, self._parts()[1])

    @property
    def metric_unit(self) -> MetricUnit:
        return getattr(MetricUnit, self._parts()[2])


@dataclasses.dataclass(frozen=True)
class Consumption:
    consumption: float = dataclasses.field(hash=False)
    unit: ConsumptionUnit
    interval_start: datetime.datetime
    interval_end: datetime.datetime

    def aggregate(self, other: 'Consumption') -> 'Consumption':
        if not isinstance(other, self.__class__):
            raise TypeError(f'Cannot add {other.__class__.__name__} to {self.__class__.__name__}')
        if self.unit != other.unit:
            raise ValueError('Cannot add different units')

        return Consumption(
            consumption=self.consumption + other.consumption,
            unit=self.unit,
            interval_start=min(self.interval_start, other.interval_start),
            interval_end=max(self.interval_end, other.interval_end),
        )

    @classmethod
    def from_json_response(cls, data: dict, unit: ConsumptionUnit) -> 'Consumption':
        interval_start = handle_datetime(data, 'interval_start')
        interval_end = handle_datetime(data, 'interval_end')
        consumption = float(data.pop('consumption'))
        # TODO(tr) warning for unexpected fields?
        return cls(
            consumption=consumption,
            unit=unit,
            interval_start=interval_start,
            interval_end=interval_end,
        )


