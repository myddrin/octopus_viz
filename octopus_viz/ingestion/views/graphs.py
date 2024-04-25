import abc
from datetime import date

from django.db.models import QuerySet
from django.http import JsonResponse, HttpRequest
from django.views import View
from django.utils.translation import gettext as _

from ingestion import models
from ingestion.aggregator.consumption import PeriodAggregator, ConsumptionAggregator, TariffAggregator
from ingestion.forms.graphs import MonthlyGraphForm


class GraphDataView(abc.ABC):
    def _plotly_layout(self, *, ylabel: str) -> dict:
        # see plot.js documentation
        return {
            'yaxis': {
                'title': ylabel,
            },
        }

    def _plotly_data(self, agg: ConsumptionAggregator, *, label: str, show_price: bool = False) -> dict:
        x_axis = []
        y_axis = []
        custom_data = []

        for key in sorted(agg.data.keys()):
            x_axis.append(key)
            row = agg.data[key]
            custom_data.append(row.as_dict())

            if show_price:
                y_axis.append(f'{row.price:.4f}')
            else:
                y_axis.append(f'{row.consumption:.4f}')

        # See plot.js documentation
        return {
            'x': x_axis,
            'y': y_axis,
            # fmt: off
            'name': label,
            # fmt: on
            'type': 'bar',
            'hovertemplate': (
                f'%{{x}}: %{{customdata.consumption:0.2f}} %{{customdata.metric_unit}}<br>'
                f'{label}: %{{customdata.price:0.2f}} %{{customdata.currency}}<br>'
                f'period: %{{customdata.earliest|%Y-%m-%d}} to %{{customdata.latest|%Y-%m-%d}}'
            ),
            'customdata': custom_data,
        }

    @classmethod
    def _info_data(cls, agg: ConsumptionAggregator, *, label: str):
        total_consumption = 0
        total_price = 0
        # derived from data
        metric_unit = ''
        currency = ''
        for entry in agg.data.values():
            total_consumption += entry.consumption
            total_price += entry.price
            metric_unit = entry.metric_unit
            currency = entry.currency

        return {
            'label': label,
            'total_consumption': f'{total_consumption:>08.4f}',
            'metric_unit': metric_unit,
            'total_price': f'{total_price:>08.4f}',
            'currency': currency,
        }

    @classmethod
    def gather_data(cls, start: date, end: date, direction: models.Direction) -> QuerySet:
        return models.Consumption.objects.filter(
            interval_start__gte=start,
            interval_start__lt=end,
            meter__mpan__direction=direction,
        ).select_related('meter__mpan')

    @abc.abstractmethod
    def build_aggregator(self, queryset: QuerySet, **kwargs) -> ConsumptionAggregator: ...

    def process_form(self, form: MonthlyGraphForm):
        data = []
        layout = {}
        import_lbl = _('import')
        export_lbl = _('export')
        info = []
        if form.is_valid():
            start_month: date = form.cleaned_data['month']
            show_price = form.cleaned_data['show_price']
            if start_month.month < 12:
                end_month = start_month.replace(month=start_month.month + 1)
            else:
                end_month = start_month.replace(month=1, year=start_month.year + 1)

            currency = ''
            metric_unit = ''
            for direction, label in (
                (models.Direction.IMPORTING, import_lbl),
                (models.Direction.EXPORTING, export_lbl),
            ):
                agg = self.build_aggregator(
                    self.gather_data(start_month, end_month, direction),
                    show_price=show_price,
                )
                data.append(
                    self._plotly_data(
                        agg,
                        label=label,
                        show_price=show_price,
                    ),
                )
                info.append(self._info_data(agg, label=label))
                currency = agg.currency
                metric_unit = agg.metric_unit

            layout = self._plotly_layout(ylabel=currency if show_price else metric_unit)

        return {
            'graph': data,
            'info': info,
            'layout': layout,
        }


class MonthlyGraphData(View, GraphDataView):
    def build_aggregator(self, queryset: QuerySet, **kwargs) -> PeriodAggregator:
        return PeriodAggregator().process(queryset)

    def get(self, request: HttpRequest):
        form = MonthlyGraphForm(request.GET)
        return JsonResponse(self.process_form(form))


class TariffGraphData(View, GraphDataView):
    def build_aggregator(self, queryset: QuerySet, *, show_price, **kwargs) -> ConsumptionAggregator:
        return TariffAggregator(by_price=show_price).process(queryset)

    def get(self, request: HttpRequest):
        form = MonthlyGraphForm(request.GET)
        return JsonResponse(self.process_form(form))
