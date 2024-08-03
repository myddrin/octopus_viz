from django import urls
from django.http import HttpRequest
from django.utils.translation import gettext as _

from ingestion.views.menu import NavbarItem, SubmenuItem


def navbar_menu(request: HttpRequest) -> dict:
    # TODO(tr) figure out how to do is_active
    menu = [
        NavbarItem.build_submenu(
            label=_('Data Visualisation'),
            submenu=[
                SubmenuItem(
                    url=urls.reverse('home'),
                    label=_('Home'),
                ),
                SubmenuItem.build_divider(),
                SubmenuItem(
                    url=urls.reverse('monthly_tariff_graph'),
                    label=_('Tariff'),
                ),
                SubmenuItem(
                    url=urls.reverse('monthly_consumption_graph'),
                    label=_('Consumption'),
                ),
            ],
        ),
        NavbarItem.build_submenu(
            label=_('Configuration'),
            submenu=[
                SubmenuItem(
                    url=urls.reverse('add_new_flux_form'),
                    label=_('New Flux tariff'),
                ),
                SubmenuItem(
                    url='',   # TODO(tr)
                    label=_('Get data from Octopus'),
                ),
            ],
        )
    ]

    return {
        'NAVBAR_MENU': menu,
    }
