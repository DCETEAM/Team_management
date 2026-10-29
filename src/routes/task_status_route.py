from flask import Blueprint
from src.controllers.task_status_controller import (
    create_task_status,
    get_all_task_statuses,
    get_task_status_by_id,
    update_task_status,
    delete_task_status,
    reorder_task_statuses,
    check_task_status_flag,
)
from src.utils.jwt import token_required
from src.utils.db_retry import with_db_reconnect

task_status_bp = Blueprint("task_status", __name__, url_prefix="/api/v1/task-statuses")

@task_status_bp.route("/", methods=["POST"])
@token_required
@with_db_reconnect
def create_task_status_route(decoded_payload):
    return create_task_status(decoded_payload)

@task_status_bp.route("/", methods=["GET"])
@token_required
@with_db_reconnect
def get_task_statuses_route(decoded_payload):
    return get_all_task_statuses(decoded_payload)

@task_status_bp.route("/reorder", methods=["PUT"])
@token_required
@with_db_reconnect
def reorder_task_statuses_route(decoded_payload):
    return reorder_task_statuses(decoded_payload)

@task_status_bp.route("/check-flag", methods=["POST"])
@token_required
@with_db_reconnect
def check_task_status_flag_route(decoded_payload):
    return check_task_status_flag(decoded_payload)

@task_status_bp.route("/<int:status_id>", methods=["GET"])
@token_required
@with_db_reconnect
def get_task_status_by_id_route(decoded_payload, status_id):
    return get_task_status_by_id(status_id, decoded_payload)

@task_status_bp.route("/<int:status_id>", methods=["PUT"])
@token_required
@with_db_reconnect
def update_task_status_route(decoded_payload, status_id):
    return update_task_status(status_id, decoded_payload)

@task_status_bp.route("/<int:status_id>", methods=["DELETE"])
@token_required
@with_db_reconnect
def delete_task_status_route(decoded_payload, status_id):    
    return delete_task_status(status_id, decoded_payload)
