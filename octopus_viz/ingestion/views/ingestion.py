import logging

from django import urls
from django.shortcuts import redirect
from django.utils import timezone
from django.views import View

from ingestion.models import IngestConsumption


logger = logging.getLogger(__name__)


class IngestOctopus(View):
    def get(self, request, **kwargs):
        # TODO(tr) would probably be better if we could enforce an authenticated user
        IngestConsumption(logger).ingest(
            None,
            timezone.now().date(),
        )
        return redirect(urls.reverse('home'))
