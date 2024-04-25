import datetime

import pytz


def handle_date(data: dict, field: str) -> datetime.date:
    return datetime.datetime.strptime(data.pop(field), "%Y-%m-%d").date()


def handle_datetime(data: dict, field: str) -> datetime.datetime:
    """Extract a tz aware datetime from data and return it as a UTC datetime"""
    octopus_datetime = datetime.datetime.fromisoformat(data.pop(field))
    if octopus_datetime.tzinfo is None:
        raise ValueError(f"Unexpected tz unaware {field} from octopus")
    return octopus_datetime.astimezone(pytz.UTC)


def handle_timedelta(data: dict, field: str) -> datetime.timedelta:
    """Extract a time delta from midnight from a string with 2 parts: '{hours}:{minutes}'"""
    kwargs = {
        k: int(v) for k, v in zip(("hours", "minutes"), data.pop(field).split(":"))
    }
    return datetime.timedelta(**kwargs)
