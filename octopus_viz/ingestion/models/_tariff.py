from django.db import models

from ._enums import EnergyType, Direction, MetricUnit


TARIFF_NAME_LENGTH = 50
CURRENCY_SIZE = 3


class Tariff(models.Model):
    name = models.CharField(max_length=TARIFF_NAME_LENGTH, unique=True)
    energy_type = models.CharField(max_length=EnergyType.max_len(), choices=EnergyType)
    metric_unit = models.CharField(max_length=MetricUnit.max_len(), choices=MetricUnit)
    direction = models.CharField(max_length=Direction.max_len(), choices=Direction)

    valid_from = models.DateField(help_text='Inclusive date - at midnight')
    valid_until = models.DateField(help_text='Exclusive date - at midnight', null=True, blank=True)
    currency = models.CharField(max_length=CURRENCY_SIZE)

    default_rate = models.FloatField(null=True, help_text='Used when rates are not found')

    def __str__(self):
        return self.name

    @property
    def unit_key(self) -> str:
        return f'{self.energy_type.label}_{self.direction.label}_{self.metric_unit.label}'


class Rate(models.Model):
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['tariff_id', 'interval_from', 'interval_end'],
                name='unique_tariff_interval',
            ),
        ]

    interval_from = models.TimeField(help_text='Inclusive time - local tz')
    interval_end = models.TimeField(help_text='Exclusive time - local tz')
    unit_rate = models.FloatField()

    tariff = models.ForeignKey(Tariff, on_delete=models.CASCADE)

    def __str__(self):
        return f'{self.tariff}[{self.interval_from} ; {self.interval_end}]'
