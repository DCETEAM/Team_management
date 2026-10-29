from flask import Blueprint
from src.controllers.task_attachment_controller import (
    create_attachment,
    get_all_attachments,
    get_attachments_by_task_id,
    get_attachment_by_id,
    update_attachment,
    delete_attachment,
    download_file,
)
from src.utils.jwt import token_required
from src.utils.db_retry import with_db_reconnect

task_attachment_bp = Blueprint("task_attachment", __name__, url_prefix="/api/v1/task_attachments")

@task_attachment_bp.route("/", methods=["POST"])
@token_required
@with_db_reconnect
def create_attachment_route(decoded_payload):
    return create_attachment(decoded_payload)

@task_attachment_bp.route("/", methods=["GET"])
@token_required
@with_db_reconnect
def get_attachments_route(decoded_payload):
    return get_all_attachments(decoded_payload)

@task_attachment_bp.route("/task/<int:task_id>", methods=["GET"])
@token_required
@with_db_reconnect
def get_attachments_by_task_id_route(decoded_payload, task_id):
    return get_attachments_by_task_id(task_id, decoded_payload)

@task_attachment_bp.route("/<int:attachment_id>", methods=["GET"])
@token_required
@with_db_reconnect
def get_attachment_by_id_route(decoded_payload, attachment_id):
    return get_attachment_by_id(attachment_id, decoded_payload)

@task_attachment_bp.route("/download/<filename>", methods=["GET"])
@token_required
@with_db_reconnect
def download_file_route(decoded_payload, filename):
    return download_file(filename, decoded_payload)

@task_attachment_bp.route("/<int:attachment_id>", methods=["PUT"])
@token_required
@with_db_reconnect
def update_attachment_route(decoded_payload, attachment_id):
    return update_attachment(attachment_id, decoded_payload)

@task_attachment_bp.route("/<int:attachment_id>", methods=["DELETE"])
@token_required
@with_db_reconnect
def delete_attachment_route(decoded_payload, attachment_id):
    return delete_attachment(attachment_id, decoded_payload)