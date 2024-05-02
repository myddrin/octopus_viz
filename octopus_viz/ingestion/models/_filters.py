from datetime import date

from django.db.models import QuerySet, Count, Q
from django.utils import timezone

from ._meter import Meter, MPAN
from ._consumption import Consumption
from ._tariff import Tariff
from ._enums import Direction, EnergyType


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

    def get_first_consumption(self) -> Consumption | None:
        return self.filter_consumptions().order_by('interval_start').first()

    def get_latest_consumption(self) -> Consumption | None:
        return self.filter_consumptions().order_by('-interval_end').first()

    @classmethod
    def meters_with_api_key(cls) -> QuerySet:
        return Meter.objects.filter(mpan__api_key__isnull=False)


class MpanFilters:
    @classmethod
    def mpan_without_api_key(cls) -> QuerySet:
        return MPAN.objects.filter(api_key__isnull=True)

    @classmethod
    def _mpan_meter_count(cls) -> QuerySet:
        return Meter.objects.annotate(attached=Count('*')).order_by('mpan').values('mpan')

    @classmethod
    def mpan_without_meter(cls) -> QuerySet:
        # select mpan_id from
        # (select mpan_id, count(*) as c from ingestion_meter group by mpan_id)
        # where c < 1;
        meter_search = cls._mpan_meter_count()
        return MPAN.objects.exclude(
            mpan__in=meter_search.filter(attached__gte=1),
        )

    # @classmethod
    # def mpan_without_recent_data(cls) -> QuerySet:
    #     meter_search = cls._mpan_meter_count()
    #     return MPAN.objects.filter(
    #         api_key__isnull=False,
    #         mpan__in=meter_search.filter(attached__gte=1).values('mpan'),
    #     )


class TariffFilters:
    @classmethod
    def current_tariff(
        cls,
        direction: Direction,
        energy_type: EnergyType,
        *,
        when: date | None = None,
    ) -> Tariff | None:
        if when is None:
            when = timezone.now().date()

        starting = Q(valid_from__isnull=True) | Q(valid_from__lte=when)
        ending = Q(valid_until__isnull=True) | Q(valid_until__gt=when)
        return Tariff.objects.filter(
            starting,
            ending,
            direction=direction,
            energy_type=energy_type,
        ).first()

    @classmethod
    def last_tariff(cls, direction: Direction, energy_type: EnergyType) -> Tariff | None:
        try:
            return Tariff.objects.filter(
                direction=direction,
                energy_type=energy_type,
            ).order_by('-valid_from')[0]
        except IndexError:
            return None
