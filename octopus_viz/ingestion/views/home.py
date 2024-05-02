import dataclasses
import logging
from typing import ClassVar, Self, Iterable

from django.shortcuts import render
from django.views import View
from django.utils.translation import gettext as _

from ingestion import models


logger = logging.getLogger(__name__)


@dataclasses.dataclass
class CardInfo:
    _success_style: ClassVar = {'class': 'bi-check-circle-fill', 'css': 'color: green'}
    _warning_style: ClassVar = {'class': 'bi-exclamation-square-fill', 'css': 'color: orange'}

    message: str
    tag: dict | None = None
    link: dict | None = None

    def as_success(self) -> Self:
        self.tag = dict(self._success_style.items())
        return self

    def as_warning(self) -> Self:
        self.tag = dict(self._warning_style.items())
        return self

    def add_link(self, url: str, html_class: str) -> Self:
        self.link = {'url': url, 'class': html_class}
        return self


class HomeView(View):
    def _consumption_cards(self) -> Iterable[CardInfo]:
        detached_consumption = models.UpdateConsumption.detached_rows(models.Consumption.objects).count()
        if detached_consumption == 0:
            yield CardInfo(_('Found no detached consumption entries')).as_success()
        else:
            # TODO(tr) If admin add link to get data from octopus?
            yield CardInfo(_('Found %(count)d detached entries') % dict(count=detached_consumption)).as_warning()

    def _mpan_cards(self) -> Iterable[CardInfo]:
        no_api_mpan = models.MpanFilters.mpan_without_api_key().count()
        no_meter_mpan = models.MpanFilters.mpan_without_meter().count()
        if no_api_mpan == 0 and no_meter_mpan == 0:
            yield CardInfo(_('MPAN configuration verified')).as_success()
        else:
            if no_api_mpan:
                # TODO(tr) If admin add link to the MPAN view
                yield CardInfo(_('Found %(count)d MPAN without API keys') % dict(count=no_api_mpan)).as_warning()
            if no_meter_mpan:
                # TODO(tr) If admin add link to add a Meter
                yield CardInfo(_('Found %(count)d MPAN without any Meter') % dict(count=no_meter_mpan)).as_warning()

    @classmethod
    def _tariff_until_message(cls, tariff: models.Tariff) -> str:
        if tariff.valid_until is None:
            return _('no termination date')
        return _('until %(until)s') % dict(until=tariff.valid_until)

    def _electricity_tariff_cards(self) -> Iterable[CardInfo]:
        current_export_tariff = models.TariffFilters.current_tariff(
            models.Direction.EXPORTING,
            models.EnergyType.ELECTRICITY,
        )
        current_import_tariff = models.TariffFilters.current_tariff(
            models.Direction.IMPORTING,
            models.EnergyType.ELECTRICITY,
        )

        if current_export_tariff is not None:
            yield CardInfo(
                _('Current exporting tariff is %(tariff_name)s (%(until_message)s)')
                % dict(
                    tariff_name=current_export_tariff.name,
                    until_message=self._tariff_until_message(current_export_tariff),
                ),
            ).as_success()
        else:
            last_export_tariff = models.TariffFilters.last_tariff(
                models.Direction.EXPORTING,
                models.EnergyType.ELECTRICITY,
            )
            if last_export_tariff is not None:
                card_message = _((
                    'Did not find any exporting tariff active today. '
                    'Last exporting tariff was %(tariff_name)s (%(until_message)s)',
                )) % dict(
                    tariff_name=last_export_tariff.name,
                    until_message=self._tariff_until_message(last_export_tariff),
                )
            else:
                card_message = _('Did not find any exporting tariff.')
            yield CardInfo(card_message).as_warning()

        if current_import_tariff is not None:
            yield CardInfo(
                _('Current importing tariff is %(tariff_name)s (%(until_message)s)')
                % dict(
                    tariff_name=current_import_tariff.name,
                    until_message=self._tariff_until_message(current_import_tariff),
                ),
            ).as_success()
        else:
            last_import_tariff = models.TariffFilters.last_tariff(
                models.Direction.IMPORTING,
                models.EnergyType.ELECTRICITY,
            )
            if last_import_tariff is not None:
                card_message = _((
                    'Did not find any importing tariff active today. '
                    'Last importing tariff was %(tariff_name)s (%(until_message)s)',
                )) % dict(
                    tariff_name=last_import_tariff.name,
                    until_message=self._tariff_until_message(last_import_tariff),
                )
            else:
                card_message = _('Did not find any importing tariff.')
            yield CardInfo(card_message).as_warning()

    def get(self, request):
        cards = [
            # TODO(tr) last entry card? with link to get more from octopus
        ]
        cards.extend(self._consumption_cards())
        cards.extend(self._mpan_cards())
        cards.extend(self._electricity_tariff_cards())

        return render(
            request,
            'ingestion/index.html',
            context={
                'title': _('Data Visualisation'),
                'cards': cards,
            },
        )
