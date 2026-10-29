from flask import Blueprint
from src.controllers.worker_controller import (
    create_worker,
    get_all_workers,
    get_worker_by_id,
    update_worker,
    delete_worker,
)
from src.utils.jwt import token_required
from src.utils.db_retry import with_db_reconnect

worker_bp = Blueprint("worker", __name__, url_prefix="/api/v1/workers")

@worker_bp.route("/", methods=["POST"])
@token_required
@with_db_reconnect
def create_worker_route(decoded_payload):
    return create_worker(decoded_payload)

@worker_bp.route("/", methods=["GET"])
@token_required
@with_db_reconnect
def get_workers_route(decoded_payload):
    return get_all_workers(decoded_payload)

@worker_bp.route("/<int:worker_id>", methods=["GET"])
@token_required
@with_db_reconnect
def get_worker_by_id_route(decoded_payload, worker_id):
    return get_worker_by_id(worker_id, decoded_payload)

@worker_bp.route("/<int:worker_id>", methods=["PUT"])
@token_required
@with_db_reconnect
def update_worker_route(decoded_payload, worker_id):
    return update_worker(worker_id, decoded_payload)

@worker_bp.route("/<int:worker_id>", methods=["DELETE"])
@token_required
@with_db_reconnect
def delete_worker_route(decoded_payload, worker_id): 
    return delete_worker(worker_id, decoded_payload)
