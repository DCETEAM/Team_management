import datetime
from collections import defaultdict

from sqlalchemy import func, or_

from src import db
from src.models.project_model import Project
from src.models.task_model import Task
from src.models.task_status_history_model import TaskStatusHistory
from src.models.task_status_model import TaskStatus
from src.utils.date_utils import parse_date
from src.utils.role_utils import get_person_details
from src.utils.allocation_utils import (
    accessible_project_ids,
    iter_task_assignees,
    filter_tasks_for_user,
    task_assigned_to_user,
)


def _payload_role(decoded_payload):
    if not decoded_payload:
        return None, None
    role = decoded_payload.get("role")
    role_id = decoded_payload.get("role_id")
    if role_id is None:
        role_id = decoded_payload.get("roleId")
    if not role:
        user_id = decoded_payload.get("user_id") or decoded_payload.get("userId")
        if user_id:
            from src.models.user_model import User

            user = User.query.get(user_id)
            if user:
                role = user.role
                role_id = role_id or user.role_id
    if role:
        role = str(role).lower().strip()
    return role, role_id


def _allowed_project_id(decoded_payload, project_id_param):
    allowed = accessible_project_ids(decoded_payload)
    raw = project_id_param
    if raw is None or raw == "" or str(raw).lower() in ("all", "0", "undefined", "null"):
        return allowed if allowed is not None else None
    try:
        pid = int(raw)
    except (TypeError, ValueError):
        return "invalid"
    if allowed is None:
        return pid
    if pid not in allowed:
        return "forbidden"
    return pid


def resolve_date_range(range_key, start_str=None, end_str=None):
    today = datetime.date.today()
    key = (range_key or "today").strip().lower().replace("-", "_")

    if key == "today":
        return today, today, None
    if key == "yesterday":
        d = today - datetime.timedelta(days=1)
        return d, d, None
    if key in ("this_week", "week"):
        start = today - datetime.timedelta(days=today.weekday())
        return start, today, None
    if key in ("this_month", "month"):
        start = today.replace(day=1)
        return start, today, None
    if key == "custom":
        start = parse_date(start_str)
        end = parse_date(end_str)
        if not start or not end:
            return None, None, "Custom range requires valid start_date and end_date (YYYY-MM-DD)"
        if isinstance(start, datetime.datetime):
            start = start.date()
        if isinstance(end, datetime.datetime):
            end = end.date()
        if start > end:
            return None, None, "start_date must be on or before end_date"
        return start, end, None

    return today, today, None


def _task_calendar_date(value):
    if value is None:
        return None
    if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
        return value
    if isinstance(value, datetime.datetime):
        return value.date()
    parsed = parse_date(value)
    if parsed is None:
        return None
    if isinstance(parsed, datetime.datetime):
        return parsed.date()
    return parsed


def task_schedule_overlaps_range(task, range_start, range_end):
    """True if task start_date → due_date overlaps [range_start, range_end] (inclusive)."""
    start = _task_calendar_date(task.start_date)
    end = _task_calendar_date(task.due_date)
    if start and end and start > end:
        start, end = end, start
    if start and not end:
        end = start
    if end and not start:
        start = end
    if not start:
        updated = _task_calendar_date(getattr(task, "updated_at", None))
        if updated is None:
            return False
        return range_start <= updated <= range_end
    return start <= range_end and end >= range_start


def _tasks_in_schedule_range(project_filter, range_start, range_end, decoded_payload):
    q = _task_query_for_projects(project_filter)
    if q is None:
        return []
    tasks = q.all()
    tasks = [t for t in tasks if task_schedule_overlaps_range(t, range_start, range_end)]
    role, role_id = _payload_role(decoded_payload)
    return filter_tasks_for_user(tasks, role, role_id)


def _task_query_for_projects(project_filter):
    q = Task.query.join(TaskStatus, Task.status_id == TaskStatus.id)
    if project_filter is not None:
        if isinstance(project_filter, int):
            q = q.filter(Task.project_id == project_filter)
        elif isinstance(project_filter, list):
            if not project_filter:
                return None
            q = q.filter(Task.project_id.in_(project_filter))
    return q


def get_project_summary(decoded_payload, project_id_param, range_key, start_str, end_str):
    project_filter = _allowed_project_id(decoded_payload, project_id_param)
    if project_filter == "invalid":
        return None, "Invalid project_id", 400
    if project_filter == "forbidden":
        return None, "You do not have access to this project", 403

    resolved = resolve_date_range(range_key, start_str, end_str)
    start, end, err = resolved
    if err:
        return None, err, 400

    if project_filter is not None and isinstance(project_filter, list) and not project_filter:
        return {
            "filters": {
                "project_id": project_id_param,
                "range": range_key,
                "start": start.isoformat(),
                "end": end.isoformat(),
            },
            "totals": {"total": 0, "completed": 0, "in_progress": 0, "todo": 0, "pending": 0, "hold": 0, "other": 0, "overdue": 0, "open": 0},
            "by_status": [],
        }, None, 200

    tasks = _tasks_in_schedule_range(project_filter, start, end, decoded_payload)
    today = datetime.date.today()

    status_counts = defaultdict(int)
    overdue_count = 0
    for task in tasks:
        status_counts[task.status_id] += 1
        if (
            task.due_date
            and task.due_date < today
            and task.status
            and not task.status.is_completed
        ):
            overdue_count += 1

    all_statuses = TaskStatus.query.order_by(TaskStatus.sort_order.asc()).all()
    by_status = []
    totals = {
        "total": len(tasks),
        "completed": 0,
        "in_progress": 0,
        "todo": 0,
        "pending": 0,
        "hold": 0,
        "other": 0,
        "overdue": overdue_count,
        "open": 0,
    }

    for st in all_statuses:
        count = status_counts.get(st.id, 0)
        if count == 0 and not status_counts:
            continue
        entry = {
            "status_id": st.id,
            "name": st.name,
            "color": st.color,
            "count": count,
            "is_completed": bool(st.is_completed),
            "is_in_progress": bool(st.is_in_progress),
            "is_todo": bool(st.is_todo),
            "is_pending": bool(st.is_pending),
            "is_hold": bool(st.is_hold),
        }
        by_status.append(entry)
        if st.is_completed:
            totals["completed"] += count
        elif st.is_in_progress:
            totals["in_progress"] += count
        elif st.is_pending:
            totals["pending"] += count
        elif st.is_hold:
            totals["hold"] += count
        elif st.is_todo:
            totals["todo"] += count
        else:
            totals["other"] += count

    totals["open"] = (
        totals["in_progress"]
        + totals["todo"]
        + totals["pending"]
        + totals["other"]
    )

    for st_id, count in status_counts.items():
        if not any(s["status_id"] == st_id for s in by_status):
            st = TaskStatus.query.get(st_id)
            if st:
                by_status.append(
                    {
                        "status_id": st.id,
                        "name": st.name,
                        "color": st.color,
                        "count": count,
                        "is_completed": bool(st.is_completed),
                        "is_in_progress": bool(st.is_in_progress),
                        "is_todo": bool(st.is_todo),
                        "is_pending": bool(st.is_pending),
                        "is_hold": bool(st.is_hold),
                    }
                )

    totals["open"] = (
        totals["in_progress"]
        + totals["todo"]
        + totals["pending"]
        + totals["other"]
    )

    return {
        "filters": {
            "project_id": None if project_filter is None and project_id_param in (None, "", "all") else project_filter,
            "range": range_key,
            "start": start.isoformat(),
            "end": end.isoformat(),
        },
        "totals": totals,
        "by_status": [s for s in by_status if s["count"] > 0],
    }, None, 200


def get_deadline_crossed_projects(decoded_payload):
    allowed = accessible_project_ids(decoded_payload)
    today = datetime.date.today()

    q = Project.query.filter(
        Project.end_date.isnot(None),
        Project.end_date < today,
        ~Project.status.in_(["completed", "cancelled"]),
    )
    if allowed is not None:
        if not allowed:
            return []
        q = q.filter(Project.id.in_(allowed))

    completed_status_ids = [
        s.id for s in TaskStatus.query.filter_by(is_completed=True).all()
    ]

    projects = q.order_by(Project.end_date.asc()).all()
    result = []
    for p in projects:
        open_q = Task.query.filter_by(project_id=p.id)
        if completed_status_ids:
            open_q = open_q.filter(~Task.status_id.in_(completed_status_ids))
        open_tasks = open_q.count()
        days_overdue = (today - p.end_date).days
        result.append(
            {
                "id": p.id,
                "name": p.name,
                "end_date": p.end_date.isoformat(),
                "days_overdue": days_overdue,
                "status": p.status,
                "open_tasks": open_tasks,
            }
        )
    return result


def _project_open_task_count(project_id, completed_status_ids):
    open_q = Task.query.filter_by(project_id=project_id)
    if completed_status_ids:
        open_q = open_q.filter(~Task.status_id.in_(completed_status_ids))
    return open_q.count()


def get_in_progress_projects(decoded_payload):
    """Active projects still within schedule (end date not passed)."""
    allowed = accessible_project_ids(decoded_payload)
    today = datetime.date.today()
    completed_status_ids = [
        s.id for s in TaskStatus.query.filter_by(is_completed=True).all()
    ]

    q = Project.query.filter(
        ~Project.status.in_(["completed", "cancelled"]),
        Project.status == "active",
        or_(Project.end_date.is_(None), Project.end_date >= today),
    )
    if allowed is not None:
        if not allowed:
            return []
        q = q.filter(Project.id.in_(allowed))

    # MySQL has no NULLS LAST; null end dates sort after dated projects.
    projects = q.order_by(Project.end_date.is_(None), Project.end_date.asc()).all()
    result = []
    for p in projects:
        days_remaining = (p.end_date - today).days if p.end_date else None
        result.append(
            {
                "id": p.id,
                "name": p.name,
                "end_date": p.end_date.isoformat() if p.end_date else None,
                "days_remaining": days_remaining,
                "status": p.status,
                "open_tasks": _project_open_task_count(p.id, completed_status_ids),
            }
        )
    return result


def _history_event_date(entry):
    d = parse_date(entry.changed_at) if entry.changed_at else None
    if d and not isinstance(d, datetime.date):
        if hasattr(d, "date"):
            d = d.date()
    if not d or isinstance(d, str):
        if entry.created_at:
            d = entry.created_at.date() if hasattr(entry.created_at, "date") else entry.created_at
    if isinstance(d, datetime.datetime):
        d = d.date()
    return d if isinstance(d, datetime.date) else None


def get_task_completions(decoded_payload, year_param, project_id_param):
    try:
        year = int(year_param) if year_param else datetime.date.today().year
    except (TypeError, ValueError):
        return None, "Invalid year", 400

    project_filter = _allowed_project_id(decoded_payload, project_id_param)
    if project_filter == "invalid":
        return None, "Invalid project_id", 400
    if project_filter == "forbidden":
        return None, "You do not have access to this project", 403

    completed_status_ids = [
        s.id for s in TaskStatus.query.filter_by(is_completed=True).all()
    ]
    if not completed_status_ids:
        return {"year": year, "counts_by_date": {}}, None, 200

    q = TaskStatusHistory.query.filter(
        TaskStatusHistory.to_status_id.in_(completed_status_ids)
    )
    if isinstance(project_filter, int):
        q = q.filter(TaskStatusHistory.project_id == project_filter)
    elif isinstance(project_filter, list):
        if not project_filter:
            return {"year": year, "counts_by_date": {}}, None, 200
        q = q.filter(TaskStatusHistory.project_id.in_(project_filter))

    counts = defaultdict(int)
    role, role_id = _payload_role(decoded_payload)
    for entry in q.all():
        d = _history_event_date(entry)
        if not d or d.year != year:
            continue
        if role == "worker" and role_id:
            task = entry.task or Task.query.get(entry.task_id)
            if task and not task_assigned_to_user(task, role, role_id):
                continue
        counts[d.isoformat()] += 1

    return {"year": year, "counts_by_date": dict(counts)}, None, 200


def _member_key(member):
    if not isinstance(member, dict):
        return f"unknown:{member}"
    uid = member.get("user_id") or member.get("role_id")
    role = member.get("role") or member.get("type") or ""
    return f"{role}:{uid}"


def get_in_progress_today(decoded_payload, project_id_param):
    project_filter = _allowed_project_id(decoded_payload, project_id_param)
    if project_filter == "invalid":
        return None, "Invalid project_id", 400
    if project_filter == "forbidden":
        return None, "You do not have access to this project", 403

    today = datetime.date.today()
    q = (
        Task.query.join(TaskStatus, Task.status_id == TaskStatus.id)
        .filter(TaskStatus.is_in_progress.is_(True))
        .filter(func.date(Task.updated_at) == today)
    )
    if isinstance(project_filter, int):
        q = q.filter(Task.project_id == project_filter)
    elif isinstance(project_filter, list):
        if not project_filter:
            return {"date": today.isoformat(), "people": []}, None, 200
        q = q.filter(Task.project_id.in_(project_filter))

    tasks = q.all()
    role, role_id = _payload_role(decoded_payload)
    tasks = filter_tasks_for_user(tasks, role, role_id)
    by_person = {}

    for task in tasks:
        members = list(iter_task_assignees(task))
        if not members:
            continue
        for member in members:
            key = _member_key(member)
            if key not in by_person:
                role = member.get("role") or member.get("type")
                role_id = member.get("role_id") or member.get("user_id")
                details = get_person_details(role, role_id) if role and role_id else None
                by_person[key] = {
                    "user_id": member.get("user_id") or role_id,
                    "role": role,
                    "first_name": details.get("first_name") if details else member.get("first_name"),
                    "last_name": details.get("last_name") if details else member.get("last_name"),
                    "email": details.get("email") if details else member.get("email"),
                    "avatar_url": details.get("avatar_url") if details else None,
                    "task_count": 0,
                    "tasks": [],
                }
            by_person[key]["task_count"] += 1
            by_person[key]["tasks"].append(
                {
                    "id": task.id,
                    "title": task.title,
                    "project_id": task.project_id,
                    "project_name": task.project.name if task.project else None,
                }
            )

    people = sorted(by_person.values(), key=lambda p: (-p["task_count"], p.get("email") or ""))
    return {"date": today.isoformat(), "people": people}, None, 200


def _tasks_in_scope(project_filter):
    q = Task.query.join(TaskStatus, Task.status_id == TaskStatus.id)
    if isinstance(project_filter, int):
        q = q.filter(Task.project_id == project_filter)
    elif isinstance(project_filter, list):
        if not project_filter:
            return []
        q = q.filter(Task.project_id.in_(project_filter))
    return q.all()


def get_project_health(decoded_payload):
    allowed = accessible_project_ids(decoded_payload)
    today = datetime.date.today()
    q = Project.query.filter(~Project.status.in_(["completed", "cancelled"]))
    if allowed is not None:
        if not allowed:
            return {"on_track": 0, "at_risk": 0, "delayed": 0, "items": []}
        q = q.filter(Project.id.in_(allowed))
    projects = q.all()
    on_track = at_risk = delayed = 0
    items = []
    for p in projects:
        if p.end_date and p.end_date < today:
            delayed += 1
            bucket = "delayed"
        elif p.end_date and (p.end_date - today).days <= 7:
            at_risk += 1
            bucket = "at_risk"
        else:
            on_track += 1
            bucket = "on_track"
        items.append(
            {
                "id": p.id,
                "name": p.name,
                "end_date": p.end_date.isoformat() if p.end_date else None,
                "health": bucket,
            }
        )
    return {"on_track": on_track, "at_risk": at_risk, "delayed": delayed, "items": items}


def get_team_activity(decoded_payload, project_id_param, range_key, start_str, end_str):
    project_filter = _allowed_project_id(decoded_payload, project_id_param)
    if project_filter == "invalid":
        return None, "Invalid project_id", 400
    if project_filter == "forbidden":
        return None, "You do not have access to this project", 403

    resolved = resolve_date_range(range_key, start_str, end_str)
    start, end, err = resolved
    if err:
        return None, err, 400

    q = _task_query_for_projects(project_filter)
    if q is None:
        return {"members": []}, None, 200

    tasks = _tasks_in_schedule_range(project_filter, start, end, decoded_payload)
    today = datetime.date.today()
    by_member = {}

    for task in tasks:
        members = list(iter_task_assignees(task))
        is_completed = bool(task.status and task.status.is_completed)
        is_overdue = bool(
            task.due_date and task.due_date < today and not is_completed
        )
        for member in members:
            key = _member_key(member)
            if key not in by_member:
                role = member.get("role") or member.get("type")
                role_id = member.get("role_id") or member.get("user_id")
                details = get_person_details(role, role_id) if role and role_id else None
                by_member[key] = {
                    "user_id": member.get("user_id") or role_id,
                    "role": role,
                    "first_name": details.get("first_name") if details else None,
                    "last_name": details.get("last_name") if details else None,
                    "email": details.get("email") if details else None,
                    "avatar_url": details.get("avatar_url") if details else None,
                    "assigned": 0,
                    "completed": 0,
                    "overdue": 0,
                }
            by_member[key]["assigned"] += 1
            if is_completed:
                by_member[key]["completed"] += 1
            if is_overdue:
                by_member[key]["overdue"] += 1

    members = []
    for row in by_member.values():
        active = max(row["assigned"] - row["completed"], 0)
        workload = min(100, int(round((active / max(row["assigned"], 1)) * 100)))
        if row["assigned"] > 0 and row["completed"] == row["assigned"]:
            workload = min(workload, 25)
        row["workload"] = workload
        members.append(row)

    members.sort(key=lambda m: (-m["assigned"], m.get("email") or ""))
    return {"members": members}, None, 200


def get_upcoming_deadlines(decoded_payload, project_id_param, limit=10):
    project_filter = _allowed_project_id(decoded_payload, project_id_param)
    if project_filter == "invalid":
        return None, "Invalid project_id", 400
    if project_filter == "forbidden":
        return None, "You do not have access to this project", 403

    today = datetime.date.today()
    q = (
        Task.query.join(TaskStatus, Task.status_id == TaskStatus.id)
        .filter(Task.due_date.isnot(None))
        .filter(Task.due_date >= today)
        .filter(TaskStatus.is_completed.is_(False))
    )
    if isinstance(project_filter, int):
        q = q.filter(Task.project_id == project_filter)
    elif isinstance(project_filter, list):
        if not project_filter:
            return {"tasks": []}, None, 200
        q = q.filter(Task.project_id.in_(project_filter))

    try:
        limit = min(int(limit), 50)
    except (TypeError, ValueError):
        limit = 10

    role, role_id = _payload_role(decoded_payload)
    tasks = q.order_by(Task.due_date.asc()).limit(max(limit * 10, 50)).all()
    tasks = filter_tasks_for_user(tasks, role, role_id)[:limit]
    result = []
    for task in tasks:
        owner = None
        assignees = list(iter_task_assignees(task))
        if assignees:
            m = assignees[0]
            role_name = m.get("role") or m.get("type")
            rid = m.get("role_id") or m.get("user_id")
            details = get_person_details(role_name, rid) if role_name and rid else None
            if details:
                owner = {
                    "first_name": details.get("first_name"),
                    "last_name": details.get("last_name"),
                    "email": details.get("email"),
                    "avatar_url": details.get("avatar_url"),
                }
        result.append(
            {
                "id": task.id,
                "title": task.title,
                "project_id": task.project_id,
                "project_name": task.project.name if task.project else None,
                "due_date": task.due_date.isoformat(),
                "priority": task.priority or "medium",
                "owner": owner,
            }
        )
    return {"tasks": result}, None, 200
