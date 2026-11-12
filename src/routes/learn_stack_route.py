from flask import Blueprint

from src.controllers.learn_stack_controller import (
    add_comment,
    create_card,
    create_domain,
    create_technology,
    delete_card,
    delete_comment,
    delete_domain,
    delete_technology,
    get_card,
    list_cards,
    list_comments,
    list_domains,
    list_technologies,
    record_card_view,
    toggle_card_like,
    update_card,
    update_domain,
    update_technology,
    upload_learn_stack_file,
)
from src.utils.db_retry import with_db_reconnect
from src.utils.jwt import token_required

learn_stack_bp = Blueprint("learn_stack", __name__, url_prefix="/api/v1/learn-stack")

# Domains
@learn_stack_bp.route("/domains", methods=["GET"])
@token_required
@with_db_reconnect
def list_domains_route(decoded_payload):
    return list_domains(decoded_payload)


@learn_stack_bp.route("/domains", methods=["POST"])
@token_required
@with_db_reconnect
def create_domain_route(decoded_payload):
    return create_domain(decoded_payload)


@learn_stack_bp.route("/domains/<int:domain_id>", methods=["PUT"])
@token_required
@with_db_reconnect
def update_domain_route(decoded_payload, domain_id):
    return update_domain(domain_id, decoded_payload)


@learn_stack_bp.route("/domains/<int:domain_id>", methods=["DELETE"])
@token_required
@with_db_reconnect
def delete_domain_route(decoded_payload, domain_id):
    return delete_domain(domain_id, decoded_payload)


# Technologies
@learn_stack_bp.route("/technologies", methods=["GET"])
@token_required
@with_db_reconnect
def list_technologies_route(decoded_payload):
    return list_technologies(decoded_payload)


@learn_stack_bp.route("/technologies", methods=["POST"])
@token_required
@with_db_reconnect
def create_technology_route(decoded_payload):
    return create_technology(decoded_payload)


@learn_stack_bp.route("/technologies/<int:technology_id>", methods=["PUT"])
@token_required
@with_db_reconnect
def update_technology_route(decoded_payload, technology_id):
    return update_technology(technology_id, decoded_payload)


@learn_stack_bp.route("/technologies/<int:technology_id>", methods=["DELETE"])
@token_required
@with_db_reconnect
def delete_technology_route(decoded_payload, technology_id):
    return delete_technology(technology_id, decoded_payload)


# Cards
@learn_stack_bp.route("/cards", methods=["GET"])
@token_required
@with_db_reconnect
def list_cards_route(decoded_payload):
    return list_cards(decoded_payload)


@learn_stack_bp.route("/cards", methods=["POST"])
@token_required
@with_db_reconnect
def create_card_route(decoded_payload):
    return create_card(decoded_payload)


@learn_stack_bp.route("/cards/<int:card_id>", methods=["GET"])
@token_required
@with_db_reconnect
def get_card_route(decoded_payload, card_id):
    return get_card(card_id, decoded_payload)


@learn_stack_bp.route("/cards/<int:card_id>", methods=["PUT"])
@token_required
@with_db_reconnect
def update_card_route(decoded_payload, card_id):
    return update_card(card_id, decoded_payload)


@learn_stack_bp.route("/cards/<int:card_id>", methods=["DELETE"])
@token_required
@with_db_reconnect
def delete_card_route(decoded_payload, card_id):
    return delete_card(card_id, decoded_payload)


@learn_stack_bp.route("/cards/<int:card_id>/view", methods=["POST"])
@token_required
@with_db_reconnect
def record_view_route(decoded_payload, card_id):
    return record_card_view(card_id, decoded_payload)


@learn_stack_bp.route("/cards/<int:card_id>/like", methods=["POST"])
@token_required
@with_db_reconnect
def toggle_like_route(decoded_payload, card_id):
    return toggle_card_like(card_id, decoded_payload)


@learn_stack_bp.route("/cards/<int:card_id>/comments", methods=["GET"])
@token_required
@with_db_reconnect
def list_comments_route(decoded_payload, card_id):
    return list_comments(card_id, decoded_payload)


@learn_stack_bp.route("/cards/<int:card_id>/comments", methods=["POST"])
@token_required
@with_db_reconnect
def add_comment_route(decoded_payload, card_id):
    return add_comment(card_id, decoded_payload)


@learn_stack_bp.route("/cards/<int:card_id>/comments/<int:comment_id>", methods=["DELETE"])
@token_required
@with_db_reconnect
def delete_comment_route(decoded_payload, card_id, comment_id):
    return delete_comment(card_id, comment_id, decoded_payload)


@learn_stack_bp.route("/upload", methods=["POST"])
@token_required
@with_db_reconnect
def upload_route(decoded_payload):
    return upload_learn_stack_file(decoded_payload)
