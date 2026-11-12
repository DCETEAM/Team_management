from datetime import date
from sqlalchemy import or_, and_
from .matching_service import person_candidates, match_name, match_simple_name
from .date_resolver import resolve_date_range
from .config import MAX_TASK_RESULTS


def _full_name(obj):
    return " ".join(x for x in [
        getattr(obj, "first_name", ""), getattr(obj, "last_name", "")
    ] if x).strip()


def _safe_value(value):
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _serialize_columns(obj, exclude=None):
    exclude = set(exclude or [])
    result = {}
    for column in obj.__table__.columns:
        name = column.name
        if name in exclude or name in {"password", "refresh_token"}:
            continue
        result[name] = _safe_value(getattr(obj, name, None))
    return result


def _related_record(model, record_id):
    if not model or record_id is None:
        return None
    obj = model.query.get(record_id)
    return obj


def _person_matches_task(task, person):
    """Check modern members JSON and legacy worker_ids JSON."""
    if not person:
        return True
    source, person_id, role = person["source"], person["id"], person["role"]

    members = getattr(task, "members", None) or []
    if isinstance(members, list):
        for member in members:
            if not isinstance(member, dict):
                continue
            try:
                mid = int(member.get("role_id"))
            except (TypeError, ValueError):
                continue
            member_role = str(member.get("role") or "").lower()
            if mid == int(person_id):
                if source == "workers" and member_role in {"worker", "team_leader", "team leader", "tl"}:
                    return True
                if source == "admins" and member_role in {"admin", "superadmin", "scrum"}:
                    return True

    if source == "workers":
        worker_ids = getattr(task, "worker_ids", None) or []
        if isinstance(worker_ids, list):
            try:
                if int(person_id) in [int(x) for x in worker_ids]:
                    return True
            except (TypeError, ValueError):
                pass
    return False


def retrieve_tasks(models, payload, today):
    Task = models["tasks"]
    Project = models["projects"]
    Status = models["task_statuses"]
    filters = payload.get("filters") or {}
    resolutions = {}

    # Resolve people against workers/admins using readable names.
    person_query = filters.get("user_name")
    person_result = match_name(
        person_query,
        person_candidates(models, filters.get("user_role"))
    )
    resolutions["user"] = person_result
    if person_result["status"] == "ambiguous":
        return [], resolutions, {
            "type": "ambiguous_person",
            "message": "More than one person matches. Please provide a fuller name or role.",
            "candidates": person_result["matches"]
        }
    if person_query and person_result["status"] == "not_found":
        return [], resolutions, {
            "type": "person_not_found",
            "message": f"No person matching '{person_query}' was found with the configured similarity threshold."
        }

    query = Task.query

    # Resolve project name.
    project_result = match_simple_name(
        filters.get("project_name"), Project.query.all(),
        lambda obj: getattr(obj, "name", "")
    )
    resolutions["project"] = project_result
    if project_result["status"] == "ambiguous":
        return [], resolutions, {
            "type": "ambiguous_project",
            "message": "Multiple projects match. Please provide a more specific project name.",
            "candidates": project_result["matches"]
        }
    if filters.get("project_name"):
        if project_result["status"] != "matched":
            return [], resolutions, {"type": "project_not_found", "message": "Project not found."}
        query = query.filter(Task.project_id == project_result["match"]["id"])

    # Resolve status by name; status aliases can also match boolean classification flags.
    status_query = filters.get("status_name")
    status_objects = Status.query.all()
    status_result = match_simple_name(
        status_query, status_objects, lambda obj: getattr(obj, "name", "")
    )
    if status_query and status_result["status"] == "not_found":
        alias = status_query.lower().replace(" ", "_")
        flag_map = {
            "completed": "is_completed", "complete": "is_completed",
            "pending": "is_pending", "in_progress": "is_in_progress",
            "review": "is_review", "on_hold": "is_hold",
            "backlog": "is_backlog", "todo": "is_todo"
        }
        flag = flag_map.get(alias)
        matching = [s for s in status_objects if flag and getattr(s, flag, False)]
        if len(matching) == 1:
            status_result = {
                "status": "matched",
                "match": {"name": matching[0].name, "id": matching[0].id, "score": 100},
                "matches": []
            }
        elif len(matching) > 1:
            status_result = {
                "status": "ambiguous", "match": None,
                "matches": [{"name": s.name, "id": s.id, "score": 100} for s in matching]
            }
    resolutions["status"] = status_result
    if status_query and status_result["status"] == "ambiguous":
        return [], resolutions, {
            "type": "ambiguous_status", "message": "The status matches multiple status records.",
            "candidates": status_result["matches"]
        }
    if status_query:
        if status_result["status"] != "matched":
            return [], resolutions, {"type": "status_not_found", "message": "Task status not found."}
        query = query.filter(Task.status_id == status_result["match"]["id"])

    # Resolve sprint by its name if the Sprint model is registered.
    sprint_query = filters.get("sprint_name")
    Sprint = models.get("sprints")
    if sprint_query and Sprint:
        sprint_objects = Sprint.query.all()
        sprint_result = match_simple_name(
            sprint_query, sprint_objects,
            lambda obj: getattr(obj, "name", getattr(obj, "title", ""))
        )
        resolutions["sprint"] = sprint_result
        if sprint_result["status"] != "matched":
            return [], resolutions, {
                "type": "sprint_not_found" if sprint_result["status"] == "not_found" else "ambiguous_sprint",
                "message": "Sprint could not be uniquely resolved.",
                "candidates": sprint_result.get("matches", [])
            }
        query = query.filter(Task.sprint_id == sprint_result["match"]["id"])

    # Task title matching is performed against the title column.
    task_name = filters.get("task_name")
    if task_name:
        query = query.filter(Task.title.ilike(f"%{task_name.strip()}%"))

    priority = filters.get("priority")
    if priority:
        query = query.filter(Task.priority.ilike(str(priority).strip()))

    # Date ranges are interpreted in Python using the configured local timezone.
    date_start, date_end = resolve_date_range(filters, today)
    if date_start or date_end:
        # Include tasks whose date span overlaps the requested period.
        # A missing start or due date does not automatically exclude a task.
        conditions = []
        if date_end:
            conditions.append(or_(Task.start_date.is_(None), Task.start_date <= date_end))
        if date_start:
            conditions.append(or_(Task.due_date.is_(None), Task.due_date >= date_start))
        if conditions:
            query = query.filter(and_(*conditions))

    # Optional creator-name matching. assigned_by_role_id is polymorphic.
    creator_query = filters.get("assigned_by_name")
    if creator_query:
        creator_candidates = person_candidates(models, filters.get("assigned_by_role"))
        creator_result = match_name(creator_query, creator_candidates)
        resolutions["assigned_by"] = creator_result
        if creator_result["status"] != "matched":
            return [], resolutions, {
                "type": "assigned_by_not_resolved",
                "message": "The task creator could not be uniquely resolved.",
                "candidates": creator_result.get("matches", [])
            }
        creator = creator_result["match"]
        role_text = str(getattr(Task, "assigned_by_role", "")).lower()
        query = query.filter(Task.assigned_by_role_id == creator["id"])
        query = query.filter(Task.assigned_by_role.ilike(creator["role"]))

    sort_column = getattr(Task, payload.get("sort_by", "due_date"), Task.due_date)
    query = query.order_by(sort_column.desc() if payload.get("sort_order") == "desc" else sort_column.asc())
    tasks = query.limit(min(int(payload.get("limit") or 50), MAX_TASK_RESULTS)).all()

    # Apply assignee matching to JSON assignment columns in Python.
    person = person_result.get("match")
    if person:
        tasks = [task for task in tasks if _person_matches_task(task, person)]

    include = set(payload.get("include") or [])
    output = []
    for task in tasks:
        project = _related_record(Project, getattr(task, "project_id", None))
        status = _related_record(Status, getattr(task, "status_id", None))
        record = {
            "task": _serialize_columns(task),
            "project_name": getattr(project, "name", None),
            "status_name": getattr(status, "name", None),
        }

        if "sub_tasks" in include:
            record["sub_tasks"] = [
                _serialize_columns(x)
                for x in getattr(task, "sub_tasks", [])
            ]
        if "comments" in include:
            record["comments"] = [
                _serialize_columns(x)
                for x in getattr(task, "comments", [])
            ]
        if "status_history" in include:
            record["status_history"] = [
                _serialize_columns(x)
                for x in getattr(task, "status_history_entries", [])
            ]
        output.append(record)

    return output, resolutions, None
