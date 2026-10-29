from flask import Blueprint
from src.controllers.meeting_controller import (
    create_meeting,
    get_all_meetings,
    get_meeting_by_id,
    update_meeting,
    delete_meeting,
)
from src.utils.jwt import token_required
from src.utils.db_retry import with_db_reconnect

meeting_bp = Blueprint("meeting", __name__, url_prefix="/api/v1/meetings")

@meeting_bp.route("/", methods=["POST"])
@token_required
@with_db_reconnect
def create_meeting_route(decoded_payload):
    return create_meeting(decoded_payload)

@meeting_bp.route("/", methods=["GET"])
@token_required
@with_db_reconnect
def get_meetings_route(decoded_payload):
    return get_all_meetings(decoded_payload)

@meeting_bp.route("/<int:meeting_id>", methods=["GET"])
@token_required
@with_db_reconnect
def get_meeting_by_id_route(decoded_payload, meeting_id):
    return get_meeting_by_id(meeting_id, decoded_payload)

@meeting_bp.route("/<int:meeting_id>", methods=["PUT"])
@token_required
@with_db_reconnect
def update_meeting_route(decoded_payload, meeting_id):
    return update_meeting(meeting_id, decoded_payload)

@meeting_bp.route("/<int:meeting_id>", methods=["DELETE"])
@token_required
@with_db_reconnect
def delete_meeting_route(decoded_payload, meeting_id):
    return delete_meeting(meeting_id, decoded_payload)
