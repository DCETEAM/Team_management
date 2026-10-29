from flask import Blueprint
from src.controllers.profile_controller import (
    get_my_profile,
    update_my_profile,
    complete_profile_onboarding,
    skip_profile_onboarding,
)
from src.utils.jwt import token_required
from src.utils.db_retry import with_db_reconnect

profile_bp = Blueprint("profile", __name__, url_prefix="/api/v1/profile")


@profile_bp.route("/me", methods=["GET"])
@token_required
@with_db_reconnect
def get_my_profile_route(decoded_payload):
    return get_my_profile(decoded_payload)


@profile_bp.route("/me", methods=["PUT"])
@token_required
@with_db_reconnect
def update_my_profile_route(decoded_payload):
    return update_my_profile(decoded_payload)


@profile_bp.route("/onboarding/complete", methods=["POST"])
@token_required
@with_db_reconnect
def complete_onboarding_route(decoded_payload):
    return complete_profile_onboarding(decoded_payload)


@profile_bp.route("/onboarding/skip", methods=["POST"])
@token_required
@with_db_reconnect
def skip_onboarding_route(decoded_payload):
    return skip_profile_onboarding(decoded_payload)
