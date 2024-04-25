from django.db import models
from django.utils.translation import gettext as _


class EnergyType(models.TextChoices):
    ELECTRICITY = 'E', _('Electricity')
    GAS = 'G', _('Gaz')

    @classmethod
    def max_len(cls) -> int:
        return max((len(k.value) for k in cls))


class Direction(models.TextChoices):
    IMPORTING = 'I', _('Importing')
    EXPORTING = 'E', _('Exporting')

    @classmethod
    def max_len(cls) -> int:
        return max((len(k.value) for k in cls))


class MetricUnit(models.TextChoices):
    KWH = 'kWh', _('kWh')
    M3 = 'm3', _('m3')

    @classmethod
    def max_len(cls) -> int:
        return max((len(k.value) for k in cls))
