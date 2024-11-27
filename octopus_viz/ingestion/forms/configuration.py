import dataclasses
from typing import Type, Optional

from django.forms import Form, DateField, ChoiceField, FloatField, BooleanField
from django.utils.translation import gettext as _

from ingestion import models
from ingestion.management.tariff_management import NewFluxTariff, FinishCurrentTariff


class NewFluxTariffForm(Form):
    """Form to add a new electricity tariff - assuming it's a flux tariff."""

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
    peak_rate = FloatField(min_value=0.0, help_text=_('Price for 1 kwh (4pm to 7pm)'))
    finish_current_tariff = BooleanField(
        initial=True,
        required=False,
        help_text=_('Finish current tariff on this tariff start date (exclusive)'),
    )

    def to_dto(self, dto_cls: Type, *, key_mapping: dict[str, str] = None) -> Optional:
        if key_mapping is None:
            key_mapping = {}
        dto_fields = {field.name for field in dataclasses.fields(dto_cls)}
        dto_data = {}
        for k, v in self.cleaned_data.items():
            dto_k = key_mapping.get(k, k)
            if dto_k in dto_fields:
                dto_data[dto_k] = v
        return dto_cls(**dto_data)

    def to_new_flux_tariff_dto(self) -> Optional[NewFluxTariff]:
        if self.is_valid():
            return self.to_dto(NewFluxTariff)

    def to_finish_current_tariff_dto(self) -> Optional[FinishCurrentTariff]:
        if self.is_valid() and self.cleaned_data['finish_current_tariff']:
            return self.to_dto(FinishCurrentTariff, key_mapping={'start_date': 'valid_until'})
