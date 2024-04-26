from django.db import models

from ._enums import EnergyType, Direction, MetricUnit

API_KEY_LENGTH = 200
DESCRIPTION_LENGTH = 200
SERIAL_LENGTH = 50


class APIKey(models.Model):
    name = models.CharField(max_length=SERIAL_LENGTH, primary_key=True, help_text='The alias for the API key')

    api_key = models.CharField(max_length=API_KEY_LENGTH)
    description = models.CharField(max_length=DESCRIPTION_LENGTH, blank=True, null=True)

    def __str__(self):
        return self.name


class MPAN(models.Model):
    mpan = models.CharField(
        max_length=SERIAL_LENGTH,
        primary_key=True,
        help_text='MPAN for electricity or MPRN for gas',
    )
    direction = models.CharField(max_length=Direction.max_len(), choices=Direction)

    description = models.CharField(max_length=DESCRIPTION_LENGTH, blank=True, null=True)

    api_key = models.ForeignKey(
        APIKey,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text='API Key - if absent no new requests to octopus are possible',
    )

    @property
    def direction_enum(self) -> Direction:
        return Direction(self.direction)

    def __str__(self):
        if self.description:
            return self.description
        return self.mpan


class Meter(models.Model):
    serial = models.CharField(max_length=SERIAL_LENGTH)
    energy_type = models.CharField(max_length=EnergyType.max_len(), choices=EnergyType)
    metric_unit = models.CharField(max_length=MetricUnit.max_len(), choices=MetricUnit)

    description = models.CharField(max_length=DESCRIPTION_LENGTH, blank=True, null=True)

    mpan = models.ForeignKey(MPAN, on_delete=models.CASCADE)

    @property
    def api_key(self) -> str:
        return self.mpan.api_key.api_key

    @property
    def energy_type_enum(self) -> EnergyType:
        return EnergyType(self.energy_type)

    @property
    def metric_unit_enum(self) -> MetricUnit:
        return MetricUnit(self.metric_unit)

    def __str__(self):
        if self.description:
            return self.description
        return self.serial
