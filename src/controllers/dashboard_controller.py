from flask import jsonify, request

from src.services import dashboard_service


def get_project_summary(decoded_payload=None):
    try:
        project_id = request.args.get("project_id")
        range_key = request.args.get("range", "today")
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")

        data, err, code = dashboard_service.get_project_summary(
            decoded_payload, project_id, range_key, start_date, end_date
        )
        if err:
            return jsonify({"status": 0, "error": err}), code
        return jsonify({"status": 1, **data}), 200
    except Exception as e:
        return jsonify({"status": 0, "error": str(e)}), 500


def get_deadline_crossed_projects(decoded_payload=None):
    try:
        projects = dashboard_service.get_deadline_crossed_projects(decoded_payload)
        return jsonify({"status": 1, "projects": projects}), 200
    except Exception as e:
        return jsonify({"status": 0, "error": str(e)}), 500


def get_in_progress_projects(decoded_payload=None):
    try:
        projects = dashboard_service.get_in_progress_projects(decoded_payload)
        return jsonify({"status": 1, "projects": projects}), 200
    except Exception as e:
        return jsonify({"status": 0, "error": str(e)}), 500


def get_task_completions(decoded_payload=None):
    try:
        year = request.args.get("year")
        project_id = request.args.get("project_id")
        data, err, code = dashboard_service.get_task_completions(
            decoded_payload, year, project_id
        )
        if err:
            return jsonify({"status": 0, "error": err}), code
        return jsonify({"status": 1, **data}), 200
    except Exception as e:
        return jsonify({"status": 0, "error": str(e)}), 500


def get_in_progress_today(decoded_payload=None):
    try:
        project_id = request.args.get("project_id")
        data, err, code = dashboard_service.get_in_progress_today(
            decoded_payload, project_id
        )
        if err:
            return jsonify({"status": 0, "error": err}), code
        return jsonify({"status": 1, **data}), 200
    except Exception as e:
        return jsonify({"status": 0, "error": str(e)}), 500


def get_project_health(decoded_payload=None):
    try:
        data = dashboard_service.get_project_health(decoded_payload)
        return jsonify({"status": 1, **data}), 200
    except Exception as e:
        return jsonify({"status": 0, "error": str(e)}), 500


def get_team_activity(decoded_payload=None):
    try:
        project_id = request.args.get("project_id")
        range_key = request.args.get("range", "today")
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")
        data, err, code = dashboard_service.get_team_activity(
            decoded_payload, project_id, range_key, start_date, end_date
        )
        if err:
            return jsonify({"status": 0, "error": err}), code
        return jsonify({"status": 1, **data}), 200
    except Exception as e:
        return jsonify({"status": 0, "error": str(e)}), 500


def get_upcoming_deadlines(decoded_payload=None):
    try:
        project_id = request.args.get("project_id")
        limit = request.args.get("limit", 10)
        data, err, code = dashboard_service.get_upcoming_deadlines(
            decoded_payload, project_id, limit
        )
        if err:
            return jsonify({"status": 0, "error": err}), code
        return jsonify({"status": 1, **data}), 200
    except Exception as e:
        return jsonify({"status": 0, "error": str(e)}), 500
