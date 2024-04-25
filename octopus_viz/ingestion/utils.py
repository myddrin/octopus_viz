# TODO(tr) Use an actual package like babel or something from django to handle other currencies
_currencies = {
    'GBP': ['£'],
    'EUR': ['€'],
    'USD': ['$'],
}
_symbol_as_suffix = {
    'EUR',
}


def format_currency(value: float, currency: str) -> str:
    """Simple currency formatting

    If the currency is know will replace the ISO currency with a symbol.
    Otherwise, the currency string is used.
    Handles prefix and suffix currencies.

    Note: GBP, EUR, USD only...
    """
    amount = f'{value:0.4f}'
    symbol = _currencies.get(currency, [f'{currency} '])[0]
    if currency in _symbol_as_suffix:
        return f'{amount}{symbol}'
    return f'{symbol}{amount}'
