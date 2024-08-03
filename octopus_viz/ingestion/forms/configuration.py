from django.forms import Form, DateField, ChoiceField, FloatField
from django.utils.translation import gettext as _

from ingestion import models


class NewFluxTariffForm(Form):
    """Form to add a new elect tariff - assuming it's a flux tariff."""
    start_date = DateField(
        input_formats=['%Y-%m-%d'],
        help_text=_('Tariff starts on that date, as YYYY-MM-DD (inclusive)'),
        # the db does not require it - but this form is to add one and the account
        #  with octopus started at some point...
        required=True,
    )
    end_date = DateField(
        input_formats=['%Y-%m-%d'],
        help_text=_('Tariff ends on that date, as YYYY-MM-DD (exclusive)'),
        required=False,  # no data is "until forever"
    )
    direction = ChoiceField(
        choices=models.Direction,
    )
    # assumes that this is a tariff with 3 values
    low_rate = FloatField(
        min_value=0.0,
        help_text=_('Price for 1 kwh (2am to 5am)'),
    )
    base_rate = FloatField(
        min_value=0.0,
        help_text=_('Price for 1 kwh (midnight to 2am, 5am to 4pm, and 7pm to midnight)'),
    )
    peak_rate = FloatField(
        min_value=0.0,
        help_text=_('Price for 1 kwh (4pm to 7pm)')
    )
