from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
from .config import APP_TIMEZONE


def local_today():
    return datetime.now(ZoneInfo(APP_TIMEZONE)).date()


def resolve_date_range(filters, today):
    """Resolve natural date presets deterministically in Python."""
    preset = filters.get("date_preset")
    start = filters.get("start_date")
    end = filters.get("end_date")

    if start:
        start = date.fromisoformat(str(start)[:10])
    if end:
        end = date.fromisoformat(str(end)[:10])

    if preset == "today":
        return today, today
    if preset == "yesterday":
        d = today - timedelta(days=1)
        return d, d
    if preset == "tomorrow":
        d = today + timedelta(days=1)
        return d, d
    if preset in {"this_week", "last_week"}:
        monday = today - timedelta(days=today.weekday())
        if preset == "last_week":
            monday -= timedelta(days=7)
        return monday, monday + timedelta(days=6)
    if preset in {"this_month", "last_month"}:
        first = today.replace(day=1)
        if preset == "last_month":
            last_previous = first - timedelta(days=1)
            first = last_previous.replace(day=1)
            return first, last_previous
        next_month = (first.replace(day=28) + timedelta(days=4)).replace(day=1)
        return first, next_month - timedelta(days=1)
    if preset == "overdue":
        return None, today - timedelta(days=1)
    if preset == "upcoming":
        return today, today + timedelta(days=30)
    if start or end:
        return start or date(1970, 1, 1), end or date(9999, 12, 31)
    return None, None
