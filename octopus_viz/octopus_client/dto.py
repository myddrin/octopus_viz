import dataclasses
import datetime
import enum
import json
from typing import Tuple, Optional, Dict, ClassVar

from octopus_viz.octopus_client import logger
from octopus_viz.octopus_client.utils import (
    handle_datetime,
    handle_timedelta,
    handle_date,
)


class EnergyType(enum.Enum):
    electricity = "electricity"
    gas = "gas"


class Direction(enum.Enum):
    importing = "importing"  # because import is a keyword
    exporting = "exporting"


class MetricUnit(enum.Enum):
    kwh = "kWh"
    m3 = "m3"


class ConsumptionUnit(enum.Enum):
    """
    A compound enum of the {EnergyType}_{Direction}_{MetricUnit}
    Not part of Octopus API
    """

    electricity_importing_kwh = "electricity_importing_kwh"
    electricity_exporting_kwh = "electricity_exporting_kwh"
    gas_importing_kwh = "gas_importing_kwh"
    gas_importing_m3 = "gas_importing_m3"

    def _parts(self) -> Tuple[str, str, str]:
        energy, direction, unit = self.name.split("_")
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
    """Data from octopus API"""

    consumption: float = dataclasses.field(hash=False)
    unit: ConsumptionUnit
    interval_start: datetime.datetime
    interval_end: datetime.datetime

    def aggregate(self, other: "Consumption") -> "Consumption":
        if not isinstance(other, self.__class__):
            raise TypeError(
                f"Cannot add {other.__class__.__name__} to {self.__class__.__name__}"
            )
        if self.unit != other.unit:
            raise ValueError("Cannot add different units")

        return Consumption(
            consumption=self.consumption + other.consumption,
            unit=self.unit,
            interval_start=min(self.interval_start, other.interval_start),
            interval_end=max(self.interval_end, other.interval_end),
        )

    @classmethod
    def from_json_response(cls, data: dict, unit: ConsumptionUnit) -> "Consumption":
        interval_start = handle_datetime(data, "interval_start")
        interval_end = handle_datetime(data, "interval_end")
        consumption = float(data.pop("consumption"))
        # TODO(tr) warning for unexpected fields?
        return cls(
            consumption=consumption,
            unit=unit,
            interval_start=interval_start,
            interval_end=interval_end,
        )


@dataclasses.dataclass
class PeriodRate:
    """Not an octopus object"""

    interval_start: datetime.timedelta
    interval_end: datetime.timedelta
    rate: float

    @classmethod
    def from_dict(cls, data: dict) -> "PeriodRate":
        rate = float(data.pop("rate"))
        interval_start = handle_timedelta(data, "interval_start")
        interval_end = handle_timedelta(data, "interval_end")

        return cls(
            interval_start=interval_start,
            interval_end=interval_end,
            rate=rate,
        )


@dataclasses.dataclass(frozen=True)
class Tariff:
    """Not an octopus object"""

    name: str
    unit: ConsumptionUnit
    currency: str
    valid_from: datetime.date
    valid_until: Optional[datetime.date]
    rates: list[PeriodRate] = dataclasses.field(default_factory=list)

    def get_rate(
        self, period_start: datetime.datetime, period_end: datetime.datetime
    ) -> Optional[float]:
        start = datetime.timedelta(hours=period_start.hour, minutes=period_start.minute)
        end = datetime.timedelta(hours=period_end.hour, minutes=period_end.minute)
        if period_end.date() > period_start.date():
            end += datetime.timedelta(hours=24)

        rates = []
        for period in self.rates:
            if (period.interval_start <= start < period.interval_end) and (
                # end periods are exclusive - which means they should be == here
                period.interval_start <= end <= period.interval_end
            ):
                rates.append(period)

        if len(rates) > 1:
            logger.warning(
                f"Too many periods for {period_start} - {period_end}: we use the most expensive"
            )
            if self.unit.direction == Direction.importing:
                return max((r.rate for r in rates))
            elif self.unit.direction == Direction.exporting:
                return min((r.rate for r in rates))
            else:
                raise ValueError(f"Unsupported {self.unit.direction=}")
        elif rates:
            return rates[0].rate

        return None

    @classmethod
    def from_dict(cls, data: dict) -> "Tariff":
        name = data.pop("name")
        currency = data.pop("currency")
        unit = ConsumptionUnit(data.pop("unit"))

        if "valid_from" in data:
            valid_from = handle_date(data, "valid_from")
        else:
            valid_from = None

        if "valid_until" in data:
            valid_until = handle_date(data, "valid_until")
        else:
            valid_until = None

        rates = [PeriodRate.from_dict(value) for value in data.pop("rates")]
        return cls(
            name=name,
            unit=unit,
            currency=currency,
            valid_from=valid_from,
            valid_until=valid_until,
            rates=rates,
        )

    @classmethod
    def tariffs_from_config(cls, data: dict) -> list["Tariff"]:
        tariff_configs = [
            cls.from_dict(meter_kwargs | {"name": name})
            for name, meter_kwargs in data.items()
        ]
        return tariff_configs


@dataclasses.dataclass(frozen=True)
class Meter:
    OCTOPUS_API_V1: ClassVar = "https://api.octopus.energy/v1"

    api_key: str
    meter_id: str
    serial: str
    unit: ConsumptionUnit
    alias: str = None

    @property
    def mpan(self) -> Optional[str]:
        """Meter Point Administration Number for electric meters"""
        if self.unit.energy_type == EnergyType.electricity:
            return self.meter_id

    @property
    def mprn(self) -> Optional[str]:
        """Meter Point Reference Number for Gas meters"""
        if self.unit.energy_type == EnergyType.gas:
            return self.meter_id

    def consumption_endpoint(self) -> str:
        if self.unit.energy_type == EnergyType.electricity:
            # TODO(tr) use urllib?
            return f"{self.OCTOPUS_API_V1}/electricity-meter-points/{self.mpan}/meters/{self.serial}/consumption"
        elif self.unit.energy_type == EnergyType.gas:
            return f"{self.OCTOPUS_API_V1}/gas-meter-points/{self.mprn}/meters/{self.serial}/consumption"
        else:
            raise NotImplementedError(f"Unexpected config {self}")

    def label(self) -> str:
        if self.alias:
            return self.alias
        return f"Meter {self.serial} ({self.unit.direction.value} {self.unit.energy_type.value})"

    @classmethod
    def from_dict(cls, data: dict) -> "Meter":
        unit = ConsumptionUnit(data.pop("unit"))  # transform to enum
        data["unit"] = unit
        if "meter_id" not in data:
            if unit.energy_type == EnergyType.electricity:
                data["meter_id"] = data.pop("mpan")
            elif unit.energy_type == EnergyType.gas:
                data["meter_id"] = data.pop("mprn")
            else:
                raise ValueError("Unexpected type of meter")
        return cls(**data)

    @classmethod
    def meters_from_config(cls, data: dict) -> list["Meter"]:
        meters_data = data.pop("meters")

        base_kwargs = {k: v for k, v in data.items()}
        meter_configs = [
            cls.from_dict(base_kwargs | meter_kwargs) for meter_kwargs in meters_data
        ]
        return meter_configs


@dataclasses.dataclass(frozen=True)
class Config:
    meters: list[Meter]
    tariffs: dict[ConsumptionUnit, list[Tariff]]

    @classmethod
    def from_json(cls, filename: str) -> "Config":
        logger.info(f'Loading configuration from "{filename}"')
        with open(filename, "r") as config_input:
            data: Dict = json.load(config_input)

        meters = Meter.meters_from_config(data.pop("meters"))

        tariffs = {}
        n_tariffs = 0
        for n_tariffs, tariff in enumerate(
            Tariff.tariffs_from_config(data.pop("tariffs")),
            start=1,
        ):
            if tariff.unit not in tariffs:
                tariffs[tariff.unit] = []
            tariffs[tariff.unit].append(tariff)

        logger.info(
            f'Loaded {len(meters)} configs and {n_tariffs} tariffs from "{filename}"'
        )
        return cls(meters=meters, tariffs=tariffs)


@dataclasses.dataclass
class ConsumptionPrice:
    consumption: Consumption
    price: float
    currency: Optional[str]

    @classmethod
    def get_rate(
        cls, consumption: Consumption, tariffs: list[Tariff]
    ) -> Tuple[float, Optional[str]]:
        for tariff in tariffs:
            if (
                tariff.valid_from is None
                or tariff.valid_from <= consumption.interval_start.date()
            ) and (
                # >= because they are both exclusive
                tariff.valid_until is None
                or tariff.valid_until >= consumption.interval_end.date()
            ):
                rate = tariff.get_rate(
                    consumption.interval_start, consumption.interval_end
                )
                if rate is None:
                    raise ValueError(
                        f"Could not find a price for {consumption} with {tariff}"
                    )
                return rate, tariff.currency
        return 0.0, None

    @classmethod
    def get_price(
        cls, consumption: Consumption, tariffs: list[Tariff]
    ) -> Tuple[float, Optional[str]]:
        rate, currency = cls.get_rate(consumption, tariffs)
        if currency is None:
            return rate, currency
        return consumption.consumption * rate, currency

    def __add__(self, other: "ConsumptionPrice"):
        if not isinstance(other, self.__class__):
            raise ValueError()
        if self.currency != other.currency and not (
            self.currency is None or other.currency is None
        ):
            raise ValueError(
                f"Cannot add two different currencies together: {self.currency} and {other.currency}"
            )
        if other.currency is not None:
            self.price += other.price
        if self.currency is None:
            self.currency = other.currency
        self.consumption = self.consumption.aggregate(other.consumption)
