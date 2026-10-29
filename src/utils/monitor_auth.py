"""Authentication helpers for desktop monitor agent."""

from functools import wraps
from flask import request, jsonify, g
from src.models.user_model import User
from src.models.monitor_models import MonitorDevice
from src.utils.jwt import decode_jwt_token, token_required


MANAGER_ROLES = frozenset({"superadmin", "admin", "scrum", "team_leader"})
from src.utils.monitor_settings import TRACKED_USER_ROLES as MONITORED_ROLES


def _parse_device_auth():
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Device "):
        raw = auth[7:].strip()
        if ":" not in raw:
            return None, None
        device_uuid, token = raw.split(":", 1)
        return device_uuid.strip(), token.strip()
    return None, None


def monitor_device_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        device_uuid, token = _parse_device_auth()
        if not device_uuid or not token:
            return jsonify({"status": 0, "msg": "Device authorization required"}), 401
        device = MonitorDevice.query.filter_by(device_uuid=device_uuid).first()
        if not device or device.status != "active":
            return jsonify({"status": 0, "msg": "Device not registered or revoked"}), 401
        if not device.verify_token(token):
            return jsonify({"status": 0, "msg": "Invalid device credentials"}), 401
        user = User.query.get(device.user_id)
        if not user or not user.is_active:
            return jsonify({"status": 0, "msg": "User inactive"}), 403
        g.monitor_device = device
        g.monitor_user = user
        g.current_user = {
            "user_id": user.id,
            "role_id": user.role_id,
            "role": user.role,
        }
        return f(*args, **kwargs)

    return decorated


def monitor_manager_required(f):
    @wraps(f)
    def decorated(decoded_payload, *args, **kwargs):
        role = (decoded_payload or {}).get("role")
        if role not in MANAGER_ROLES:
            return jsonify({"status": 0, "msg": "Manager access required"}), 403
        return f(decoded_payload, *args, **kwargs)

    return token_required(decorated)


def monitor_employee_jwt_required(f):
    @wraps(f)
    def decorated(decoded_payload, *args, **kwargs):
        role = (decoded_payload or {}).get("role")
        if role not in MONITORED_ROLES and role not in MANAGER_ROLES:
            return jsonify({"status": 0, "msg": "Monitoring not enabled for this role"}), 403
        return f(decoded_payload, *args, **kwargs)

    return token_required(decorated)
