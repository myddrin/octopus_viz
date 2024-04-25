import abc
from typing import Iterable, Self

from django.utils.translation import gettext as _

from ingestion import models
from ingestion.aggregator.dto import ConsumptionPrice
from ingestion.utils import format_currency


class ConsumptionAggregator(abc.ABC):
    def __init__(self):
        self.data: dict[str, ConsumptionPrice] = {}
        self._metric_unit: str | None = None
        self._currency: str | None = None

    @property
    def metric_unit(self) -> str | None:
        return self._metric_unit

    @property
    def currency(self) -> str | None:
        return self._currency

    @abc.abstractmethod
    def _key(self, row: models.Consumption): ...

    @classmethod
    def _convert(cls, row: models.Consumption) -> ConsumptionPrice:
        return ConsumptionPrice(
            row.consumption,
            row.meter.metric_unit_enum.label,
            row.interval_start,
            row.interval_end,
            row.cost,
            row.currency,
        )

    def process(self, data: Iterable[models.Consumption]) -> Self:
        for raw_data in data:
            item = self._convert(raw_data)
            key = self._key(raw_data)
            present = self.data.get(key)
            if present is None:
                self.data[key] = item
            else:
                present += item

            # TODO(tr) This assume we only have one unit and one currency
            if self._metric_unit is None:
                self._metric_unit = item.metric_unit
            if self._currency is None:
                self._currency = item.currency

        return self


class PeriodAggregator(ConsumptionAggregator):
    def __init__(self, interval_start_fmt: str = '%H:%M'):
        super().__init__()
        self.interval_start_fmt = interval_start_fmt

    def _key(self, row: models.Consumption) -> str:
        if row.rate is None:
            # label when there is no rate
            return _('detached')
        return row.interval_start.strftime(self.interval_start_fmt)


class TariffAggregator(ConsumptionAggregator):
    interval_from_fmt = '%H:%M'

    def __init__(self, by_price: bool = True):
        super().__init__()
        self.by_price = by_price

    def _key(self, row: models.Consumption) -> str:
        if self.by_price:
            return format_currency(row.rate.unit_rate, row.tariff.currency)
        st = row.rate.interval_from.strftime(self.interval_from_fmt)
        ed = row.rate.interval_end.strftime(self.interval_from_fmt)
        return f'{st} - {ed}'
