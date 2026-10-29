from flask import Blueprint
from src.controllers.leave_request_controller import (
    create_leave_request,
    get_all_leave_requests,
    get_my_leave_requests,
    get_leave_request_by_id,
    review_leave_request,
    cancel_leave_request,
    delete_leave_request,
    upload_attachment
)
from src.utils.jwt import token_required
from src.utils.db_retry import with_db_reconnect

leave_request_bp = Blueprint("leave", __name__, url_prefix="/api/v1/leave")

@leave_request_bp.route("/", methods=["POST"])
@token_required
@with_db_reconnect
def create_leave_request_route(decoded_payload):
    return create_leave_request(decoded_payload)

@leave_request_bp.route("/", methods=["GET"])
@token_required
@with_db_reconnect
def get_all_leave_requests_route(decoded_payload):
    return get_all_leave_requests(decoded_payload)

@leave_request_bp.route("/my", methods=["GET"])
@token_required
@with_db_reconnect
def get_my_leave_requests_route(decoded_payload):
    return get_my_leave_requests(decoded_payload)

@leave_request_bp.route("/<int:leave_id>", methods=["GET"])
@token_required
@with_db_reconnect
def get_leave_request_by_id_route(decoded_payload, leave_id):
    return get_leave_request_by_id(leave_id, decoded_payload)

@leave_request_bp.route("/<int:leave_id>/review", methods=["PUT"])
@token_required
@with_db_reconnect
def review_leave_request_route(decoded_payload, leave_id):
    return review_leave_request(leave_id, decoded_payload)

@leave_request_bp.route("/<int:leave_id>/cancel", methods=["PUT"])
@token_required
@with_db_reconnect
def cancel_leave_request_route(decoded_payload, leave_id):
    return cancel_leave_request(leave_id, decoded_payload)

@leave_request_bp.route("/<int:leave_id>", methods=["DELETE"])
@token_required
@with_db_reconnect
def delete_leave_request_route(decoded_payload, leave_id):
    return delete_leave_request(leave_id, decoded_payload)

@leave_request_bp.route("/upload", methods=["POST"])
@token_required
@with_db_reconnect
def upload_attachment_route(decoded_payload):
    return upload_attachment(decoded_payload)
