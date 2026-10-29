from flask import Blueprint
from src.controllers.project_excel_controller import (
    create_project_excel,
    get_all_project_excels,
    get_excel_by_id,
    get_excels_by_project_id,
    update_project_excel,
    delete_project_excel,
)
from src.utils.jwt import token_required
from src.utils.db_retry import with_db_reconnect

project_excel_bp = Blueprint("project_excel", __name__, url_prefix="/api/v1/project-excels")

@project_excel_bp.route("/", methods=["POST"])
@token_required
@with_db_reconnect
def create_project_excel_route(decoded_payload):
    return create_project_excel(decoded_payload)

@project_excel_bp.route("/", methods=["GET"])
@token_required
@with_db_reconnect
def get_all_project_excels_route(decoded_payload):
    return get_all_project_excels(decoded_payload)

@project_excel_bp.route("/<int:excel_id>", methods=["GET"])
@token_required
@with_db_reconnect
def get_excel_by_id_route(decoded_payload, excel_id):
    return get_excel_by_id(excel_id, decoded_payload)

@project_excel_bp.route("/project/<int:project_id>", methods=["GET"])
@token_required
@with_db_reconnect
def get_excels_by_project_id_route(decoded_payload, project_id):
    return get_excels_by_project_id(project_id, decoded_payload)

@project_excel_bp.route("/<int:excel_id>", methods=["PUT"])
@token_required
@with_db_reconnect
def update_project_excel_route(decoded_payload, excel_id):
    return update_project_excel(excel_id, decoded_payload)

@project_excel_bp.route("/<int:excel_id>", methods=["DELETE"])
@token_required
@with_db_reconnect
def delete_project_excel_route(decoded_payload, excel_id):
    return delete_project_excel(excel_id, decoded_payload)
