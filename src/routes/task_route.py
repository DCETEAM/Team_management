from flask import Blueprint
from src.controllers.task_controller import (
    create_task,
    get_all_tasks,
    get_tasks_by_project,
    get_tasks_by_sprint,
    get_task_by_id,
    update_task,
    delete_task,
    get_dashboard_tasks,
    get_project_backlog,
)
from src.utils.jwt import token_required
from src.utils.db_retry import with_db_reconnect

task_bp = Blueprint("task", __name__, url_prefix="/api/v1/tasks")

@task_bp.route("/", methods=["POST"])
@token_required
@with_db_reconnect
def create_task_route(decoded_payload):
    return create_task(decoded_payload)

@task_bp.route("/", methods=["GET"])
@token_required
@with_db_reconnect
def get_tasks_route(decoded_payload):
    return get_all_tasks(decoded_payload)

@task_bp.route("/project/<int:project_id>", methods=["GET"])
@token_required
@with_db_reconnect
def get_tasks_by_project_route(decoded_payload, project_id):
    return get_tasks_by_project(project_id, decoded_payload)

@task_bp.route("/sprint/<int:sprint_id>", methods=["GET"])
@token_required
@with_db_reconnect
def get_tasks_by_sprint_route(decoded_payload, sprint_id):
    return get_tasks_by_sprint(sprint_id, decoded_payload)

@task_bp.route("/<int:task_id>", methods=["GET"])
@token_required
@with_db_reconnect
def get_task_by_id_route(decoded_payload, task_id):
    return get_task_by_id(task_id, decoded_payload)

@task_bp.route("/<int:task_id>", methods=["PUT"])
@token_required
@with_db_reconnect
def update_task_route(decoded_payload, task_id):
    return update_task(task_id, decoded_payload)

@task_bp.route("/<int:task_id>", methods=["DELETE"])
@token_required
@with_db_reconnect
def delete_task_route(decoded_payload, task_id):
    return delete_task(task_id, decoded_payload)

@task_bp.route("/dashboard", methods=["GET"])
@token_required
@with_db_reconnect
def get_dashboard_tasks_route(decoded_payload):
    return get_dashboard_tasks(decoded_payload)


@task_bp.route("/project/<int:project_id>/backlog", methods=["GET"])
@token_required
@with_db_reconnect
def get_project_backlog_route(decoded_payload, project_id):
    return get_project_backlog(project_id, decoded_payload)
