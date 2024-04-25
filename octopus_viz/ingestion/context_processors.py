from django import urls
from django.http import HttpRequest
from django.utils.translation import gettext as _

from ingestion.views.menu import NavbarItem, SubmenuItem


def navbar_menu(request: HttpRequest) -> dict:
    # TODO(tr) figure out how to do is_active
    menu = [
        # NavbarItem(
        #     url=urls.reverse('index'),
        #     label='Ingestion',
        # ),
        NavbarItem.build_submenu(
            label=_('Data Visualisation'),
            submenu=[
                SubmenuItem(
                    url=urls.reverse('index'),
                    label=_('Index'),
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
    ]

    return {
        'NAVBAR_MENU': menu,
    }
