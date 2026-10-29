from flask import Blueprint, request
from src.controllers.project_task_controller import get_project_task_data
from src.utils.jwt import token_required
from src.utils.db_retry import with_db_reconnect

project_task_bp = Blueprint("project_task", __name__, url_prefix="/api/v1/project-tasks")

@project_task_bp.route("/project/<int:project_id>", methods=["GET"])
@token_required
@with_db_reconnect
def get_project_task_data_route(decoded_payload, project_id):
    sprint_id = request.args.get("sprintId")
    if sprint_id:
        sprint_id = int(sprint_id)
    return get_project_task_data(project_id, sprint_id, decoded_payload)
