"""Apply device clock from HTTP requests to persisted rows (projects, monitor, etc.)."""

from flask import jsonify

from src.utils.monitor_client_time import get_client_now_from_request

CLIENT_TIME_MSG = (
    "Missing or invalid client time. Send X-Client-Time (ISO-8601) "
    "or client_time in the JSON body."
)


def require_client_now(req):
    dt = get_client_now_from_request(req)
    if not dt:
        return None, (jsonify({"status": 0, "msg": CLIENT_TIME_MSG}), 400)
    return dt, None


def stamp_model_times(model, req, *, creating=False):
    """Set created_at / updated_at from the client clock before commit."""
    now, err = require_client_now(req)
    if err:
        return err
    if creating and hasattr(model, "created_at"):
        model.created_at = now
    if hasattr(model, "updated_at"):
        model.updated_at = now
    return None


def touch_updated_at(model, req):
    now, err = require_client_now(req)
    if err:
        return err
    if hasattr(model, "updated_at"):
        model.updated_at = now
    return None
