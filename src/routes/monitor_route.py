from flask import Blueprint
from src.utils.jwt import token_required
from src.utils.monitor_auth import (
    monitor_device_required,
    monitor_manager_required,
    monitor_employee_jwt_required,
)
from src.controllers.monitor_controller import (
    get_monitor_policy,
    create_pairing_code,
    register_device,
    revoke_my_devices,
    start_session,
    session_heartbeat,
    session_events,
    session_break_start,
    session_break_end,
    end_session,
    me_today,
    manager_live,
    manager_timeline,
    manager_daily_report,
    analytics_overview,
    analytics_user_insight,
)

monitor_bp = Blueprint("monitor", __name__, url_prefix="/api/v1/monitor")


@monitor_bp.route("/policy", methods=["GET"])
@token_required
def policy_route(decoded_payload):
    return get_monitor_policy(decoded_payload)


@monitor_bp.route("/pairing/code", methods=["POST"])
@monitor_employee_jwt_required
def pairing_code_route(decoded_payload):
    return create_pairing_code(decoded_payload)


@monitor_bp.route("/devices/register", methods=["POST"])
def register_device_route():
    return register_device()


@monitor_bp.route("/devices/revoke-mine", methods=["POST"])
@monitor_employee_jwt_required
def revoke_my_devices_route(decoded_payload):
    return revoke_my_devices(decoded_payload)


@monitor_bp.route("/sessions/start", methods=["POST"])
@monitor_device_required
def start_session_route():
    return start_session()


@monitor_bp.route("/sessions/<int:session_id>/heartbeat", methods=["POST"])
@monitor_device_required
def heartbeat_route(session_id):
    return session_heartbeat(session_id)


@monitor_bp.route("/sessions/<int:session_id>/events", methods=["POST"])
@monitor_device_required
def events_route(session_id):
    return session_events(session_id)


@monitor_bp.route("/sessions/<int:session_id>/break/start", methods=["POST"])
@monitor_device_required
def break_start_route(session_id):
    return session_break_start(session_id)


@monitor_bp.route("/sessions/<int:session_id>/break/end", methods=["POST"])
@monitor_device_required
def break_end_route(session_id):
    return session_break_end(session_id)


@monitor_bp.route("/sessions/<int:session_id>/end", methods=["POST"])
@monitor_device_required
def end_session_route(session_id):
    return end_session(session_id)


@monitor_bp.route("/me/today", methods=["GET"])
@token_required
def me_today_route(decoded_payload):
    return me_today(decoded_payload)


@monitor_bp.route("/manager/live", methods=["GET"])
@monitor_manager_required
def manager_live_route(decoded_payload):
    return manager_live(decoded_payload)


@monitor_bp.route("/manager/employees/<int:employee_id>/timeline", methods=["GET"])
@monitor_manager_required
def manager_timeline_route(decoded_payload, employee_id):
    return manager_timeline(decoded_payload, employee_id)


@monitor_bp.route("/manager/reports/daily", methods=["GET"])
@monitor_manager_required
def manager_daily_report_route(decoded_payload):
    return manager_daily_report(decoded_payload)


@monitor_bp.route("/analytics/overview", methods=["GET"])
@token_required
def analytics_overview_route(decoded_payload):
    return analytics_overview(decoded_payload)


@monitor_bp.route("/analytics/users/<int:user_id>", methods=["GET"])
@token_required
def analytics_user_insight_route(decoded_payload, user_id):
    return analytics_user_insight(decoded_payload, user_id)
