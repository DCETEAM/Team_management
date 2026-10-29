from flask import Blueprint
from src.controllers.project_member_controller import get_project_members
from src.utils.jwt import token_required
from src.utils.db_retry import with_db_reconnect

project_member_bp = Blueprint("project_member", __name__, url_prefix="/api/v1/project-members")

@project_member_bp.route("/project/<int:project_id>", methods=["GET"])
@token_required
@with_db_reconnect
def get_project_members_route(decoded_payload, project_id):
    return get_project_members(project_id, decoded_payload)
