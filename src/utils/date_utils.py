import datetime

def parse_date(date_str):
    if not date_str:
        return None
    
    # If already a date/datetime object
    if isinstance(date_str, (datetime.date, datetime.datetime)):
        return date_str
        
    formats = [
        "%Y-%m-%d",                # 2026-05-04
        "%a, %d %b %Y %H:%M:%S GMT", # Mon, 04 May 2026 00:00:00 GMT
        "%Y-%m-%dT%H:%M:%S.%fZ",   # 2026-05-04T18:26:36.988Z
        "%Y-%m-%dT%H:%M:%S",       # 2026-05-04T18:26:36
    ]
    
    for fmt in formats:
        try:
            return datetime.datetime.strptime(date_str, fmt).date()
        except (ValueError, TypeError):
            continue
            
    return date_str # Return as is if no format matches, SQLAlchemy might handle it or fail later


def safe_isoformat(date_val):
    """Serialize date/datetime for JSON; pass through strings from legacy DB rows."""
    if date_val is None:
        return None
    if isinstance(date_val, str):
        return date_val
    try:
        if hasattr(date_val, "isoformat"):
            return date_val.isoformat()
        return str(date_val)
    except Exception:
        return str(date_val)
