from flask import Blueprint
from src.controllers.project_allocation_controller import (
    create_allocation,
    get_all_allocations,
    get_allocation_by_id,
    get_allocation_by_project_id,
    update_allocation,
    update_allocation_members,
    delete_allocation,
    get_available_users_by_project,
)
from src.utils.jwt import token_required
from src.utils.db_retry import with_db_reconnect

project_allocation_bp = Blueprint("project_allocation", __name__, url_prefix="/api/v1/project-allocations")

@project_allocation_bp.route("/", methods=["POST"])
@token_required
@with_db_reconnect
def create_allocation_route(decoded_payload):
    return create_allocation(decoded_payload)

@project_allocation_bp.route("/", methods=["GET"])
@token_required
@with_db_reconnect
def get_allocations_route(decoded_payload):
    return get_all_allocations(decoded_payload)

@project_allocation_bp.route("/<int:allocation_id>", methods=["GET"])
@token_required
@with_db_reconnect
def get_allocation_by_id_route(decoded_payload, allocation_id):      
    return get_allocation_by_id(allocation_id, decoded_payload)

@project_allocation_bp.route("/project/<int:project_id>", methods=["GET"])
@token_required
@with_db_reconnect
def get_allocation_by_project_id_route(decoded_payload, project_id):
    return get_allocation_by_project_id(project_id, decoded_payload)

@project_allocation_bp.route("/<int:allocation_id>", methods=["PUT"])
@token_required
@with_db_reconnect
def update_allocation_route(decoded_payload, allocation_id):
    return update_allocation(allocation_id, decoded_payload)

@project_allocation_bp.route("/<int:allocation_id>/members", methods=["PUT"])
@token_required
@with_db_reconnect
def update_allocation_members_route(decoded_payload, allocation_id):
    return update_allocation_members(allocation_id, decoded_payload)

@project_allocation_bp.route("/project/<int:project_id>/available-users", methods=["GET"])
@token_required
@with_db_reconnect
def get_available_users_by_project_route(decoded_payload, project_id):
    return get_available_users_by_project(project_id, decoded_payload)

@project_allocation_bp.route("/<int:allocation_id>", methods=["DELETE"])
@token_required
@with_db_reconnect
def delete_allocation_route(decoded_payload, allocation_id):
    return delete_allocation(allocation_id, decoded_payload)
