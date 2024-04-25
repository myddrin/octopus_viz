from django import urls
from django.contrib.admin import ModelAdmin
from django.db.models import Count
from django.utils.html import format_html

from ingestion import models
from ingestion.models import MeterFilters
from ingestion.utils import format_currency


class APIKeyAdminView(ModelAdmin):
    list_display = (
        'name',
        'description',
        'associated_mpan',
    )
    ordering = ('name',)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(
            associated_mpan_count=Count('mpan'),
        )
        return queryset

    @classmethod
    def associated_mpan(cls, obj: models.APIKey):
        return obj.associated_mpan_count


class MPANAdminView(ModelAdmin):
    list_display = (
        'mpan',
        'direction',
        'description',
        'has_api_key',
        'attached_meters_link',
        'readings_link',
        'last_reading',
    )
    ordering = ('mpan',)
    search_fields = ('mpan',)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(
            attached_api_key_count=Count('api_key'),
            attached_meter_count=Count('meter'),
        )
        return queryset

    @classmethod
    def has_api_key(cls, obj: models.MPAN):
        return bool(obj.attached_api_key_count)

    @classmethod
    def attached_meters_link(cls, obj: models.MPAN):
        url = urls.reverse(f'admin:{obj._meta.app_label}_meter_changelist') + f'?q={obj.mpan}'
        return format_html(f'<a class="viewlink" href="{url}">{obj.attached_meter_count} meters</a>')

    @classmethod
    def readings_link(cls, obj: models.MPAN):
        url = urls.reverse(f'admin:{obj._meta.app_label}_consumption_changelist') + f'?q={obj.mpan}'
        # TODO(tr) as part of the query instead of post query
        number_of_readings = models.Consumption.objects.filter(meter__mpan=obj).count()
        return format_html(f'<a class="viewlink" href="{url}">{number_of_readings} readings</a>')

    @classmethod
    def last_reading(cls, obj: models.MPAN):
        # TODO(tr) as part of the query instead of post query
        return MeterFilters(obj).get_latest_consumption()


class MeterAdminView(ModelAdmin):
    list_display = (
        'serial',
        'energy_type',
        'metric_unit',
        'description',
        'mpan_link',
        # 'mpan__direction',
        'readings_link',
        'last_reading',
    )
    search_fields = ('serial', 'mpan__mpan')
    list_select_related = ('mpan',)
    # ordering = ('-last_reading',)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(
            reading_count=Count('consumption'),
        )
        return queryset

    @classmethod
    def mpan_link(cls, obj: models.Meter):
        url = urls.reverse(f'admin:{obj._meta.app_label}_mpan_changelist') + f'?q={obj.mpan.mpan}'
        return format_html(f'<a class="viewlink" href="{url}">{obj.mpan}</a>')

    @classmethod
    def readings_link(cls, obj: models.MPAN):
        url = urls.reverse(f'admin:{obj._meta.app_label}_consumption_changelist') + f'?q={obj.serial}'
        # number_of_readings = models.Consumption.objects.filter(meter=obj).count()
        return format_html(f'<a class="viewlink" href="{url}">{obj.reading_count} readings</a>')

    @classmethod
    def last_reading(cls, obj: models.Meter):
        # TODO(tr) as part of the query instead of post query
        return MeterFilters(obj).get_latest_consumption()


class ConsumptionAdminView(ModelAdmin):
    list_display = ('interval_start', 'meter_link', 'mpan_link', 'value', 'charge', 'tariff_link', 'unit_rate')
    search_fields = ('meter__serial', 'meter__mpan__mpan')
    ordering = (
        '-interval_start',
        'meter__serial',
    )
    list_select_related = ('meter', 'meter__mpan', 'rate')
    readonly_fields = [field.name for field in models.Consumption._meta.get_fields()]

    @classmethod
    def value(cls, obj: models.Consumption):
        return f'{obj.consumption} {obj.meter.metric_unit_enum.label} {obj.meter.mpan.direction}'

    @classmethod
    def charge(cls, obj: models.Consumption):
        if obj.cost is not None:
            value = obj.cost
            if obj.meter.mpan.direction_enum == models.Direction.EXPORTING:
                value *= -1
            return format_currency(value, obj.currency)
        return None

    @classmethod
    def metric_unit(cls, obj: models.Consumption):
        return obj.meter.metric_unit_enum

    @classmethod
    def meter_link(cls, obj: models.Consumption):
        url = urls.reverse(f'admin:{obj._meta.app_label}_meter_changelist') + f'?q={obj.meter.serial}'
        return format_html(f'<a class="viewlink" href="{url}">{obj.meter}</a>')

    @classmethod
    def mpan_link(cls, obj: models.Consumption):
        url = urls.reverse(f'admin:{obj._meta.app_label}_mpan_changelist') + f'?q={obj.meter.mpan.mpan}'
        return format_html(f'<a class="viewlink" href="{url}">{obj.meter.mpan}</a>')

    @classmethod
    def tariff_link(cls, obj: models.Consumption):
        if obj.tariff:
            url = urls.reverse(f'admin:{obj._meta.app_label}_tariff_changelist') + f'?q={obj.tariff.name}'
            return format_html(f'<a class="viewlink" href="{url}">{obj.tariff}</a>')
        return None

    @classmethod
    def unit_rate(cls, obj: models.Consumption):
        if obj.rate:
            return f'{obj.rate.unit_rate:.4f}'
        elif obj.tariff:
            return 'default rate'
        return None


class TariffAdminView(ModelAdmin):
    list_display = (
        'name',
        'energy_type',
        'direction',
        'valid_from',
        'valid_until',
        'default_rate',
        'currency',
        'rates',
    )
    search_fields = ('name',)
    ordering = (
        '-valid_from',
        'energy_type',
        'direction',
    )

    @classmethod
    def rates(cls, obj: models.Tariff):
        n_rates = models.Rate.objects.filter(tariff=obj).count()
        label = f'{n_rates} rates'
        if n_rates < 0:
            return label
        url = urls.reverse(f'admin:{obj._meta.app_label}_rate_changelist') + f'?q={obj.name}'
        return format_html(f'<a class="viewlink" href="{url}">{label}</a>')


class RateAdminView(ModelAdmin):
    list_display = (
        'interval_from',
        'interval_end',
        'unit_rate',
        'tariff_currency',
        'tariff_link',
    )
    search_fields = ('tariff__name',)
    list_select_related = ('tariff',)
    ordering = (
        'tariff',
        'interval_from',
    )

    @classmethod
    def tariff_link(cls, obj: models.Rate):
        url = urls.reverse(f'admin:{obj._meta.app_label}_tariff_changelist') + f'q={obj.tariff.name}'
        return format_html(f'<a class="viewlink" href="{url}">{obj.tariff}')

    @classmethod
    def tariff_currency(cls, obj: models.Rate):
        return obj.tariff.currency
