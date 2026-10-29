from flask import Blueprint
from src.controllers.client_controller import (
    create_client,
    get_all_clients,
    get_client_by_id,
    update_client,
    delete_client,
)
from src.utils.jwt import token_required
from src.utils.db_retry import with_db_reconnect

client_bp = Blueprint("client", __name__, url_prefix="/api/v1/clients")

@client_bp.route("/", methods=["POST"])
@token_required
@with_db_reconnect
def create_client_route(decoded_payload):
    return create_client(decoded_payload)

@client_bp.route("/", methods=["GET"])
@token_required
@with_db_reconnect
def get_clients_route(decoded_payload):
    return get_all_clients(decoded_payload)

@client_bp.route("/<int:client_id>", methods=["GET"])
@token_required
@with_db_reconnect
def get_client_by_id_route(decoded_payload, client_id):
    return get_client_by_id(client_id, decoded_payload)

@client_bp.route("/<int:client_id>", methods=["PUT"])
@token_required
@with_db_reconnect
def update_client_route(decoded_payload, client_id):
    return update_client(client_id, decoded_payload)

@client_bp.route("/<int:client_id>", methods=["DELETE"])
@token_required
@with_db_reconnect
def delete_client_route(decoded_payload, client_id):
    return delete_client(client_id, decoded_payload)
