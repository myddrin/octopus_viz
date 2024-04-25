from django import forms
from django.utils.translation import gettext as _


class MonthlyGraphForm(forms.Form):
    month = forms.DateField(
        input_formats=['%Y-%m'],
        help_text=_('The month as YYYY-MM'),
        localize=True,
    )
    show_price = forms.BooleanField(localize=True, required=False)
