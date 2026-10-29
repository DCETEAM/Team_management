from flask import Blueprint
from src.controllers.meeting_message_controller import (
    create_message,
    get_messages_by_meeting,
    get_message_by_id,
    update_message,
    delete_message,
)
from src.utils.jwt import token_required
from src.utils.db_retry import with_db_reconnect

meeting_message_bp = Blueprint("meeting_message", __name__, url_prefix="/api/v1/meeting_messages")

@meeting_message_bp.route("/", methods=["POST"])
@token_required
@with_db_reconnect
def create_message_route(decoded_payload):
    return create_message(decoded_payload)

@meeting_message_bp.route("/meeting/<int:meeting_id>", methods=["GET"])
@token_required
@with_db_reconnect
def get_messages_by_meeting_route(decoded_payload, meeting_id):
    return get_messages_by_meeting(meeting_id, decoded_payload)

@meeting_message_bp.route("/<int:message_id>", methods=["GET"])
@token_required
@with_db_reconnect
def get_message_by_id_route(decoded_payload, message_id):
    return get_message_by_id(message_id, decoded_payload)

@meeting_message_bp.route("/<int:message_id>", methods=["PUT"])
@token_required
@with_db_reconnect
def update_message_route(decoded_payload, message_id):
    return update_message(message_id, decoded_payload)

@meeting_message_bp.route("/<int:message_id>", methods=["DELETE"])
@token_required
@with_db_reconnect
def delete_message_route(decoded_payload, message_id):
    return delete_message(message_id, decoded_payload)
