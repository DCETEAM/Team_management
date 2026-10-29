"""Parse timestamps from clients — server must not invent 'now' for monitor writes."""

import datetime
import re

CLIENT_TIME_HEADER = "X-Client-Time"
CLIENT_LOCAL_DATE_HEADER = "X-Client-Local-Date"


def parse_client_datetime(val):
    if val is None or val == "":
        return None
    if isinstance(val, datetime.datetime):
        return val.replace(tzinfo=None) if val.tzinfo else val
    text = str(val).strip()
    if not text:
        return None
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        dt = datetime.datetime.fromisoformat(text)
        if dt.tzinfo is not None:
            dt = dt.astimezone(datetime.timezone.utc).replace(tzinfo=None)
        return dt
    except ValueError:
        return None


def parse_client_local_date(val):
    if not val:
        return None
    text = str(val).strip()
    if re.match(r"^\d{4}-\d{2}-\d{2}$", text):
        try:
            return datetime.datetime.strptime(text, "%Y-%m-%d").date()
        except ValueError:
            return None
    dt = parse_client_datetime(val)
    return dt.date() if dt else None


def get_client_now_from_request(request):
    header_val = request.headers.get(CLIENT_TIME_HEADER)
    if header_val:
        parsed = parse_client_datetime(header_val)
        if parsed:
            return parsed
    data = request.get_json(silent=True) if request else None
    if isinstance(data, dict):
        for key in ("client_time", "received_at", "occurred_at"):
            if data.get(key):
                parsed = parse_client_datetime(data.get(key))
                if parsed:
                    return parsed
    return None


def get_client_work_date_from_request(request):
    local_hdr = request.headers.get(CLIENT_LOCAL_DATE_HEADER)
    if local_hdr:
        d = parse_client_local_date(local_hdr)
        if d:
            return d
    day = request.args.get("date") if request else None
    if day:
        d = parse_client_local_date(day)
        if d:
            return d
    now = get_client_now_from_request(request)
    if now:
        return now.date()
    return None


def format_dt_z(dt):
    if not dt:
        return None
    return dt.isoformat() + "Z"
