import logging

from django import urls
from django.http import HttpRequest
from django.shortcuts import render, redirect
from django.views import View
from django.utils.translation import gettext as _

from ingestion import models
from ingestion.forms.configuration import NewFluxTariffForm
from ingestion.management.tariff_management import add_new_flux_tariff, finish_current_tariff
from ingestion.views.utils import TariffCardsFactory

logger = logging.getLogger(__name__)


class AddOctopusTariffView(View):
    def get(self, request: HttpRequest):
        form = NewFluxTariffForm()
        cards = list(TariffCardsFactory.electricity_tariff_cards())

        return render(
            request,
            'admin/add_flux_tariff.html',
            context={
                'form': form,
                'post_url': urls.reverse('process_new_flux_form'),
                'title': _('Add a new Flux tariff'),
                'cards': cards,
            },
        )


class ProcessOctopusTariffView(View):
    def post(self, request: HttpRequest):
        form = NewFluxTariffForm(request.POST)
        if new_flux_params := form.to_new_flux_tariff_dto():
            current_tariff = models.TariffFilters.current_tariff(
                models.Direction(new_flux_params.direction),
                models.EnergyType.ELECTRICITY,
            )

            name = add_new_flux_tariff(new_flux_params)
            logger.info(f'Created {name}')

            # TODO(tr) handle name=None when integrity error was caught
            # TODO(tr) handle redirect to page with the new tariff information
            if current_tariff is not None and (finish_current_params := form.to_finish_current_tariff_dto()):
                finished = finish_current_tariff(current_tariff, finish_current_params)
                # TODO(tr) handle finish=None when the tariff had an end date
                logger.info(f'Finished {finished} on {finish_current_params.valid_until}')

        return redirect(urls.reverse('add_new_flux_form'))
