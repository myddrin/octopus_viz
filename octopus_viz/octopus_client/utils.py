import datetime

import pytz


def handle_datetime(data: dict, field: str) -> datetime.datetime:
    """Extract a tz aware datetime from data and return it as a UTC datetime"""
    octopus_datetime = datetime.datetime.fromisoformat(data.pop(field))
    if octopus_datetime.tzinfo is None:
        raise ValueError(f'Unexpected tz unaware {field} from octopus')
    return octopus_datetime.astimezone(pytz.UTC)
