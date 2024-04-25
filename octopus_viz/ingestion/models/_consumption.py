from django.db import models

from ._meter import Meter
from ._tariff import Rate, Tariff


class Consumption(models.Model):
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['meter_id', 'interval_start', 'interval_end'],
                name='unique_consumption_interval',
            ),
        ]

    consumption = models.FloatField()
    interval_start = models.DateTimeField(help_text='Interval start - inclusive')
    interval_end = models.DateTimeField(help_text='Interval end - exclusive')

    meter = models.ForeignKey(Meter, on_delete=models.CASCADE)
    tariff = models.ForeignKey(Tariff, null=True, default=None, on_delete=models.SET_NULL)
    rate = models.ForeignKey(Rate, null=True, default=None, on_delete=models.SET_NULL)

    def __str__(self):
        return f'{self.meter}[{self.interval_start} - {self.interval_end}]'

    @property
    def cost(self) -> float | None:
        if self.rate:
            return self.consumption * self.rate.unit_rate
        if self.tariff and self.tariff.default_rate:
            return self.consumption * self.tariff.default_rate
        return None

    @property
    def currency(self) -> str | None:
        if self.tariff:
            return self.tariff.currency
        return None
