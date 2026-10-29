from flask import Blueprint
from src.controllers.task_status_history_controller import get_sprint_status_history
from src.utils.jwt import token_required
from src.utils.db_retry import with_db_reconnect

task_status_history_bp = Blueprint(
    "task_status_history", __name__, url_prefix="/api/v1/sprints"
)


@task_status_history_bp.route("/<int:sprint_id>/status-history", methods=["GET"])
@token_required
@with_db_reconnect
def get_sprint_status_history_route(decoded_payload, sprint_id):
    return get_sprint_status_history(sprint_id, decoded_payload)
