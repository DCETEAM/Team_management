from flask import jsonify, request
from src import db
from src.models.task_status_history_model import TaskStatusHistory
from src.models.sprint_model import Sprint
from src.utils.date_utils import safe_isoformat
from src.utils.project_permissions import is_admin_role
from src.utils.monitor_client_time import get_client_time_raw_from_request


def record_task_status_change(
    task, old_status_id, new_status_id, old_status, new_status, decoded_payload
):
    if old_status_id == new_status_id:
        return

    role_id = decoded_payload.get("role_id") if decoded_payload else None
    role = decoded_payload.get("role") if decoded_payload else None

    from src.utils.role_utils import get_person_details

    person = get_person_details(role, role_id) if role and role_id else None

    client_when = get_client_time_raw_from_request(request)

    entry = TaskStatusHistory(
        task_id=task.id,
        project_id=task.project_id,
        sprint_id=task.sprint_id,
        task_title=task.title,
        from_status_id=old_status_id,
        to_status_id=new_status_id,
        from_status_name=old_status.name if old_status else None,
        to_status_name=new_status.name if new_status else None,
        changed_by_role_id=role_id,
        changed_by_role=role,
        changed_by_first_name=person.get("first_name") if person else None,
        changed_by_last_name=person.get("last_name") if person else None,
        changed_by_email=person.get("email") if person else None,
        changed_at=client_when,
    )
    db.session.add(entry)


def get_sprint_status_history(sprint_id, decoded_payload=None):
    try:
        role = decoded_payload.get("role") if decoded_payload else None
        if not is_admin_role(role):
            return jsonify(
                {
                    "msg": "Only administrators can view sprint status history",
                    "status": 0,
                    "restricted": True,
                }
            ), 403

        sprint = Sprint.query.get(sprint_id)
        if not sprint:
            return jsonify({"message": "Sprint not found", "status": 0}), 404

        rows = (
            TaskStatusHistory.query.filter_by(sprint_id=sprint_id)
            .order_by(TaskStatusHistory.id.desc())
            .all()
        )

        result = []
        for row in rows:
            when = row.changed_at if row.changed_at else safe_isoformat(row.created_at)
            result.append(
                {
                    "id": row.id,
                    "task_id": row.task_id,
                    "task_title": row.task_title,
                    "project_id": row.project_id,
                    "sprint_id": row.sprint_id,
                    "from_status_id": row.from_status_id,
                    "to_status_id": row.to_status_id,
                    "from_status_name": row.from_status_name,
                    "to_status_name": row.to_status_name,
                    "changed_by": {
                        "role_id": row.changed_by_role_id,
                        "role": row.changed_by_role,
                        "first_name": row.changed_by_first_name,
                        "last_name": row.changed_by_last_name,
                        "email": row.changed_by_email,
                    },
                    "changed_at": when,
                    "created_at": when,
                }
            )

        return jsonify({"history": result, "status": 1}), 200
    except Exception as e:
        return jsonify({"success": 0, "error": str(e)}), 500
