import dataclasses
from typing import ClassVar, Self, Iterable

from ingestion import models

from django.utils.translation import gettext as _


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

    def add_link(self, url: str, label: str, html_class: str) -> Self:
        self.link = {'url': url, 'label': label, 'class': html_class}
        return self


class TariffCardsFactory:
    @classmethod
    def _tariff_until_message(cls, tariff: models.Tariff) -> str:
        if tariff.valid_until is None:
            return _('no termination date')
        return _('until %(until)s') % dict(until=tariff.valid_until)

    @classmethod
    def electricity_tariff_cards(cls) -> Iterable[CardInfo]:
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
                    until_message=cls._tariff_until_message(current_export_tariff),
                ),
            ).as_success()
        else:
            last_export_tariff = models.TariffFilters.last_tariff(
                models.Direction.EXPORTING,
                models.EnergyType.ELECTRICITY,
            )
            if last_export_tariff is not None:
                card_message = _(
                    'Did not find any exporting tariff active today. '
                    'Last exporting tariff was %(tariff_name)s (%(until_message)s)',
                ) % dict(
                    tariff_name=last_export_tariff.name,
                    until_message=cls._tariff_until_message(last_export_tariff),
                )
            else:
                card_message = _('Did not find any exporting tariff.')
            yield CardInfo(card_message).as_warning()

        if current_import_tariff is not None:
            yield CardInfo(
                _('Current importing tariff is %(tariff_name)s (%(until_message)s)')
                % dict(
                    tariff_name=current_import_tariff.name,
                    until_message=cls._tariff_until_message(current_import_tariff),
                ),
            ).as_success()
        else:
            last_import_tariff = models.TariffFilters.last_tariff(
                models.Direction.IMPORTING,
                models.EnergyType.ELECTRICITY,
            )
            if last_import_tariff is not None:
                card_message = _(
                    'Did not find any importing tariff active today. '
                    'Last importing tariff was %(tariff_name)s (%(until_message)s)',
                ) % dict(
                    tariff_name=last_import_tariff.name,
                    until_message=cls._tariff_until_message(last_import_tariff),
                )
            else:
                card_message = _('Did not find any importing tariff.')
            yield CardInfo(card_message).as_warning()
