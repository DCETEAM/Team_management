from flask import Blueprint
from src.controllers.task_comment_controller import (
    create_comment,
    get_comments_by_task,
    get_comment_by_id,
    update_comment,
    delete_comment,
)
from src.utils.jwt import token_required
from src.utils.db_retry import with_db_reconnect

task_comment_bp = Blueprint("task_comment", __name__, url_prefix="/api/v1/task-comments")

@task_comment_bp.route("/", methods=["POST"])
@token_required
@with_db_reconnect
def create_comment_route(decoded_payload):
    return create_comment(decoded_payload)

@task_comment_bp.route("/task/<int:task_id>", methods=["GET"])
@token_required
@with_db_reconnect
def get_comments_by_task_route(decoded_payload, task_id):
    return get_comments_by_task(task_id, decoded_payload)

@task_comment_bp.route("/<int:comment_id>", methods=["GET"])
@token_required
@with_db_reconnect
def get_comment_by_id_route(decoded_payload, comment_id):
    return get_comment_by_id(comment_id, decoded_payload)

@task_comment_bp.route("/<int:comment_id>", methods=["PUT"])
@token_required
@with_db_reconnect
def update_comment_route(decoded_payload, comment_id):
    return update_comment(comment_id, decoded_payload)

@task_comment_bp.route("/<int:comment_id>", methods=["DELETE"])
@token_required
@with_db_reconnect
def delete_comment_route(decoded_payload, comment_id):
    return delete_comment(comment_id, decoded_payload)
