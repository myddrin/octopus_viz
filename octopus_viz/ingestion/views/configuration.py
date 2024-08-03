from django import urls
from django.http import HttpRequest
from django.shortcuts import render, redirect
from django.views import View
from django.utils.translation import gettext as _

from ingestion.forms.configuration import NewFluxTariffForm


class AddOctopusTariffView(View):

    def get(self, request: HttpRequest):
        form = NewFluxTariffForm()
        return render(
            request,
            'admin/add_flux_tariff.html',
            context={
                'form': form,
                'post_url': urls.reverse('process_new_tariff'),
                'title': _('Add a new Flux tariff'),
            }
        )


class ProcessOctopusTariffView(View):
    def post(self, request: HttpRequest):
        form = NewFluxTariffForm(request.POST)
        if form.is_valid():
            pass
        else:
            return redirect(urls.reverse('add_new_tariff'))
