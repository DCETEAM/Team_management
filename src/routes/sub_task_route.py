from flask import Blueprint
from src.controllers.sub_task_controller import (
    create_sub_task,
    get_all_sub_tasks,
    get_sub_tasks_by_task_id,
    get_sub_task_by_id,
    update_sub_task,
    delete_sub_task,
)
from src.utils.jwt import token_required
from src.utils.db_retry import with_db_reconnect

sub_task_bp = Blueprint("sub_task", __name__, url_prefix="/api/v1/sub-tasks")

@sub_task_bp.route("/", methods=["POST"])
@token_required
@with_db_reconnect
def create_sub_task_route(decoded_payload):
    return create_sub_task(decoded_payload)

@sub_task_bp.route("/", methods=["GET"])
@token_required
@with_db_reconnect
def get_sub_tasks_route(decoded_payload):
    return get_all_sub_tasks(decoded_payload)

@sub_task_bp.route("/task/<int:task_id>", methods=["GET"])
@token_required
@with_db_reconnect
def get_sub_tasks_by_task_id_route(decoded_payload, task_id):
    return get_sub_tasks_by_task_id(task_id, decoded_payload)

@sub_task_bp.route("/<int:sub_task_id>", methods=["GET"])
@token_required
@with_db_reconnect
def get_sub_task_by_id_route(decoded_payload, sub_task_id):
    return get_sub_task_by_id(sub_task_id, decoded_payload)

@sub_task_bp.route("/<int:sub_task_id>", methods=["PUT"])
@token_required
@with_db_reconnect
def update_sub_task_route(decoded_payload, sub_task_id):
    return update_sub_task(sub_task_id, decoded_payload)

@sub_task_bp.route("/<int:sub_task_id>", methods=["DELETE"])
@token_required
@with_db_reconnect
def delete_sub_task_route(decoded_payload, sub_task_id):
    return delete_sub_task(sub_task_id, decoded_payload)
