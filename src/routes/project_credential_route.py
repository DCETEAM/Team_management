from flask import Blueprint

from src.controllers.project_credential_controller import (
    create_project_credential,
    delete_project_credential,
    list_project_credentials,
    update_project_credential,
)
from src.utils.db_retry import with_db_reconnect
from src.utils.jwt import token_required

project_credential_bp = Blueprint(
    "project_credential", __name__, url_prefix="/api/v1/project-credentials"
)


@project_credential_bp.route("/", methods=["GET"])
@token_required
@with_db_reconnect
def list_credentials_route(decoded_payload):
    return list_project_credentials(decoded_payload)


@project_credential_bp.route("/", methods=["POST"])
@token_required
@with_db_reconnect
def create_credential_route(decoded_payload):
    return create_project_credential(decoded_payload)


@project_credential_bp.route("/<int:credential_id>", methods=["PUT"])
@token_required
@with_db_reconnect
def update_credential_route(decoded_payload, credential_id):
    return update_project_credential(credential_id, decoded_payload)


@project_credential_bp.route("/<int:credential_id>", methods=["DELETE"])
@token_required
@with_db_reconnect
def delete_credential_route(decoded_payload, credential_id):
    return delete_project_credential(credential_id, decoded_payload)
