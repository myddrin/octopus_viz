import logging
from datetime import timedelta
from typing import Iterable

from django import urls
from django.conf import settings
from django.db.models import Max
from django.utils import timezone
from django.utils.translation import gettext as _, ngettext
from django.views.generic import TemplateView

from ingestion import models
from ingestion.views.utils import TariffCardsFactory, CardInfo

logger = logging.getLogger(__name__)


class HomeView(TemplateView):
    template_name = 'ingestion/index.html'

    def _last_entry_card(self) -> Iterable[CardInfo]:
        last_entries = models.Consumption.objects.values('meter_id').annotate(
            last_loaded=Max('interval_start'),
        )
        outdated_meters = 0
        threshold = timedelta(days=settings.OFFER_DATA_DOWNLOAD_AFTER_DAYS)
        for row in last_entries:
            meter_name = str(models.Meter.objects.get(id=row['meter_id']))
            when = row['last_loaded'].date().isoformat()
            card = CardInfo(
                _('Last entry for %(meter)s was on %(when)s') % dict(meter=meter_name, when=when),
            )
            if timezone.now() - row['last_loaded'] >= threshold:
                outdated_meters += 1
                yield card.as_warning()
            else:
                yield card.as_success()

        if outdated_meters:
            yield (
                CardInfo(
                    ngettext(
                        '%(n_outdated)d meter do not have updates for more than %(settings)d days.',
                        '%(n_outdated)d meters do not have updates for more than %(settings)d days.',
                        outdated_meters,
                    )
                    % dict(n_outdated=outdated_meters, settings=threshold.days),
                )
                .add_link(
                    urls.reverse('ingestion_octopus'),
                    'Retrieve more data',
                    'btn btn-outline-success',
                )
                .as_warning()
            )

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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cards: list[CardInfo] = list(self._last_entry_card())
        cards.extend(self._consumption_cards())
        cards.extend(self._mpan_cards())
        cards.extend(TariffCardsFactory.electricity_tariff_cards())

        context.update({
            'title': _('Data Visualisation'),
            'cards': cards,
        })
        return context
