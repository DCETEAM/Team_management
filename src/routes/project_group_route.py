from flask import Blueprint
from src.controllers.project_group_controller import (
    create_project_group,
    get_all_project_groups,
    get_project_group_by_id,
    update_project_group,
    delete_project_group,
    add_projects_to_group
)
from src.utils.jwt import token_required
from src.utils.db_retry import with_db_reconnect

project_group_bp = Blueprint("project_group", __name__, url_prefix="/api/v1/project-groups")

@project_group_bp.route("/", methods=["POST"])
@token_required
@with_db_reconnect
def create_group_route(decoded_payload):
    return create_project_group(decoded_payload)

@project_group_bp.route("/", methods=["GET"])
@token_required
@with_db_reconnect
def get_groups_route(decoded_payload):
    return get_all_project_groups(decoded_payload)

@project_group_bp.route("/<int:group_id>", methods=["GET"])
@token_required
@with_db_reconnect
def get_group_by_id_route(decoded_payload, group_id):
    return get_project_group_by_id(group_id, decoded_payload)

@project_group_bp.route("/<int:group_id>", methods=["PUT"])
@token_required
@with_db_reconnect
def update_group_route(decoded_payload, group_id):
    return update_project_group(group_id, decoded_payload)

@project_group_bp.route("/<int:group_id>", methods=["DELETE"])
@token_required
@with_db_reconnect
def delete_group_route(decoded_payload, group_id):
    return delete_project_group(group_id, decoded_payload)

@project_group_bp.route("/<int:group_id>/add-projects", methods=["POST"])
@token_required
@with_db_reconnect
def add_projects_route(decoded_payload, group_id):
    return add_projects_to_group(group_id, decoded_payload)
