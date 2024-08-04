from django.forms import DateField, Form, BooleanField
from django.utils.translation import gettext as _


class MonthlyGraphForm(Form):
    month = DateField(
        input_formats=['%Y-%m'],
        help_text=_('The month as YYYY-MM'),
        localize=True,
    )
    show_price = BooleanField(localize=True, required=False)
