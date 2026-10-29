from flask import Blueprint
from src.controllers.project_controller import (
    create_project,
    get_all_projects,
    get_project_by_id,
    update_project,
    delete_project,
)
from src.utils.jwt import token_required
from src.utils.db_retry import with_db_reconnect

project_bp = Blueprint("project", __name__, url_prefix="/api/v1/projects")

@project_bp.route("/", methods=["POST"])
@token_required
@with_db_reconnect
def create_project_route(decoded_payload):
    return create_project(decoded_payload)

@project_bp.route("/", methods=["GET"])
@token_required
@with_db_reconnect
def get_projects_route(decoded_payload):
    return get_all_projects(decoded_payload)

@project_bp.route("/<int:project_id>", methods=["GET"])
@token_required
@with_db_reconnect
def get_project_by_id_route(decoded_payload, project_id):
    return get_project_by_id(project_id, decoded_payload)

@project_bp.route("/<int:project_id>", methods=["PUT"])
@token_required
@with_db_reconnect
def update_project_route(decoded_payload, project_id):
    return update_project(project_id, decoded_payload)

@project_bp.route("/<int:project_id>", methods=["DELETE"])
@token_required
@with_db_reconnect
def delete_project_route(decoded_payload, project_id):
    return delete_project(project_id, decoded_payload)
