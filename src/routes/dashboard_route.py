from flask import Blueprint

from src.controllers.dashboard_controller import (
    get_deadline_crossed_projects,
    get_in_progress_today,
    get_project_health,
    get_project_summary,
    get_task_completions,
    get_team_activity,
    get_upcoming_deadlines,
)
from src.utils.db_retry import with_db_reconnect
from src.utils.jwt import token_required

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/api/v1/dashboard")


@dashboard_bp.route("/project-summary", methods=["GET"])
@token_required
@with_db_reconnect
def project_summary_route(decoded_payload):
    return get_project_summary(decoded_payload)


@dashboard_bp.route("/deadline-crossed-projects", methods=["GET"])
@token_required
@with_db_reconnect
def deadline_crossed_route(decoded_payload):
    return get_deadline_crossed_projects(decoded_payload)


@dashboard_bp.route("/task-completions", methods=["GET"])
@token_required
@with_db_reconnect
def task_completions_route(decoded_payload):
    return get_task_completions(decoded_payload)


@dashboard_bp.route("/in-progress-today", methods=["GET"])
@token_required
@with_db_reconnect
def in_progress_today_route(decoded_payload):
    return get_in_progress_today(decoded_payload)


@dashboard_bp.route("/project-health", methods=["GET"])
@token_required
@with_db_reconnect
def project_health_route(decoded_payload):
    return get_project_health(decoded_payload)


@dashboard_bp.route("/team-activity", methods=["GET"])
@token_required
@with_db_reconnect
def team_activity_route(decoded_payload):
    return get_team_activity(decoded_payload)


@dashboard_bp.route("/upcoming-deadlines", methods=["GET"])
@token_required
@with_db_reconnect
def upcoming_deadlines_route(decoded_payload):
    return get_upcoming_deadlines(decoded_payload)
