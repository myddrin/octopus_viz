import logging
from typing import Iterable

from django.shortcuts import render
from django.views import View
from django.utils.translation import gettext as _

from ingestion import models
from ingestion.views.utils import TariffCardsFactory, CardInfo

logger = logging.getLogger(__name__)


class HomeView(View):
    def _consumption_cards(self) -> Iterable[CardInfo]:
        detached_consumption = models.UpdateConsumption.gather_detached_rows(models.Consumption.objects).count()
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

    def get(self, request):
        cards: list[CardInfo] = [
            # TODO(tr) last entry card? with link to get more from octopus
        ]
        cards.extend(self._consumption_cards())
        cards.extend(self._mpan_cards())
        cards.extend(TariffCardsFactory.electricity_tariff_cards())

        return render(
            request,
            'ingestion/index.html',
            context={
                'title': _('Data Visualisation'),
                'cards': cards,
            },
        )
