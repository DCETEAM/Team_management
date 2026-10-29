from flask import Blueprint
from src.controllers.activity_log_controller import (
    get_all_activity_logs,
    get_logs_by_user,
    get_logs_by_table,
)
from src.utils.jwt import token_required
from src.utils.db_retry import with_db_reconnect

activity_log_bp = Blueprint("activity_log", __name__, url_prefix="/api/v1/activity_logs")

@activity_log_bp.route("/", methods=["GET"])
@token_required
@with_db_reconnect
def get_all_logs_route(decoded_payload):
    return get_all_activity_logs(decoded_payload)

@activity_log_bp.route("/user/<int:user_id>", methods=["GET"])
@token_required
@with_db_reconnect
def get_user_logs_route(decoded_payload, user_id):
    return get_logs_by_user(user_id, decoded_payload)

@activity_log_bp.route("/table/<string:table_name>", methods=["GET"])
@token_required
@with_db_reconnect
def get_table_logs_route(decoded_payload, table_name):
    return get_logs_by_table(table_name, decoded_payload)
