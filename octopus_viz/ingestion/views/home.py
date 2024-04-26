from django.shortcuts import render
from django.views import View
from django.utils.translation import gettext as _

from ingestion import models


class IndexView(View):
    def get(self, request):
        detached_consumption = models.UpdateConsumption.detached_rows(models.Consumption.objects).count()

        detached_card = {
            'message': _('Found %(count)d detached entries') % dict(count=detached_consumption),
        }
        if detached_consumption == 0:
            detached_card['tag'] = {'class': 'bi-check-circle-fill', 'css': 'color: green'}
        else:
            detached_card['tag'] = {'class': 'bi-exclamation-square-fill', 'css': 'color: orange'}

        return render(
            request,
            'ingestion/index.html',
            context={
                'title': _('Data Visualisation'),
                'cards': [
                    detached_card,  # TODO(tr) add link to update
                    # last entry card? with link to get more from octopus
                    # no current tariff card? with link to add tariff
                ],
            },
        )
