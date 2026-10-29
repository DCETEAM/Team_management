from flask import Blueprint
from src.controllers.sprint_controller import (
    create_sprint,
    get_all_sprints,
    get_sprint_by_id,
    update_sprint,
    delete_sprint,
    start_sprint,
    end_sprint,
    start_sprint_with_move,
)
from src.utils.jwt import token_required
from src.utils.db_retry import with_db_reconnect

sprint_bp = Blueprint("sprint", __name__, url_prefix="/api/v1/sprints")

@sprint_bp.route("/", methods=["POST"])
@token_required
@with_db_reconnect
def create_sprint_route(decoded_payload):
    return create_sprint(decoded_payload)

@sprint_bp.route("/", methods=["GET"])
@token_required
@with_db_reconnect
def get_sprints_route(decoded_payload):
    return get_all_sprints(decoded_payload)

@sprint_bp.route("/<int:sprint_id>", methods=["GET"])
@token_required
@with_db_reconnect
def get_sprint_by_id_route(decoded_payload, sprint_id):
    return get_sprint_by_id(sprint_id, decoded_payload)

@sprint_bp.route("/<int:sprint_id>", methods=["PUT"])
@token_required
@with_db_reconnect
def update_sprint_route(decoded_payload, sprint_id):
    return update_sprint(sprint_id, decoded_payload)

@sprint_bp.route("/<int:sprint_id>", methods=["DELETE"])
@token_required
@with_db_reconnect
def delete_sprint_route(decoded_payload, sprint_id):    
    return delete_sprint(sprint_id, decoded_payload)

@sprint_bp.route("/<int:sprint_id>/start", methods=["POST"])
@token_required
@with_db_reconnect
def start_sprint_route(decoded_payload, sprint_id):
    return start_sprint(sprint_id, decoded_payload)

@sprint_bp.route("/<int:sprint_id>/end", methods=["POST"])
@token_required
@with_db_reconnect
def end_sprint_route(decoded_payload, sprint_id):
    return end_sprint(sprint_id, decoded_payload)

@sprint_bp.route("/<int:sprint_id>/start-with-move", methods=["POST"])
@token_required
@with_db_reconnect
def start_sprint_with_move_route(decoded_payload, sprint_id):
    return start_sprint_with_move(sprint_id, decoded_payload)
