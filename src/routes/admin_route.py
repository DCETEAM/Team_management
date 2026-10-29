from flask import Blueprint
from src.controllers.admin_controller import (
    create_admin,
    get_all_admins,
    get_admin_by_id,
    update_admin,
    delete_admin,
)
from src.utils.jwt import token_required
from src.utils.db_retry import with_db_reconnect

admin_bp = Blueprint("admin", __name__, url_prefix="/api/v1/admins")

@admin_bp.route("/", methods=["POST"])
@token_required
@with_db_reconnect
def create_admin_route(decoded_payload):
    return create_admin(decoded_payload)

@admin_bp.route("/", methods=["GET"])
@token_required
@with_db_reconnect
def get_admins_route(decoded_payload):
    return get_all_admins(decoded_payload)

@admin_bp.route("/<int:admin_id>", methods=["GET"])
@token_required
@with_db_reconnect
def get_admin_by_id_route(decoded_payload, admin_id):
    return get_admin_by_id(admin_id, decoded_payload)

@admin_bp.route("/<int:admin_id>", methods=["PUT"])
@token_required
@with_db_reconnect
def update_admin_route(decoded_payload, admin_id):
    return update_admin(admin_id, decoded_payload)

@admin_bp.route("/<int:admin_id>", methods=["DELETE"])
@token_required
@with_db_reconnect
def delete_admin_route(decoded_payload, admin_id):
    return delete_admin(admin_id, decoded_payload)
