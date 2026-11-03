"""Project allocation and task assignee helpers (workers, team leaders)."""


def normalize_role_name(role):
    if not role:
        return ""
    return str(role).strip().lower().replace(" ", "_").replace("-", "_")


def member_record_id(member):
    """Worker/admin id stored on allocation or task assignee."""
    if not isinstance(member, dict):
        return None
    uid = member.get("user_id")
    if uid is None:
        uid = member.get("role_id")
    if uid is None:
        return None
    try:
        return int(uid)
    except (TypeError, ValueError):
        return None


def match_allocation_member(member, role, role_id):
    """True if this allocation member row is the logged-in worker/TL/admin."""
    if not isinstance(member, dict):
        return False
    if role_id is None:
        return False
    mid = member_record_id(member)
    if mid is None:
        return False
    try:
        if int(mid) != int(role_id):
            return False
    except (TypeError, ValueError):
        return False

    mrole = normalize_role_name(member.get("role") or member.get("type"))
    role = normalize_role_name(role)

    if role in ("superadmin", "admin", "scrum"):
        return mrole in ("superadmin", "admin", "scrum", "") or not mrole
    if role == "team_leader":
        return mrole in ("team_leader", "tl", "teamleader", "") or not mrole
    if role == "worker":
        return mrole in ("worker", "") or not mrole
    return True


def accessible_project_ids(decoded_payload):
    """None = all projects; [] = none."""
    if not decoded_payload:
        return []

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
        role = normalize_role_name(role)

    if role in ("superadmin", "admin", "scrum"):
        return None
    if role in ("team_leader", "worker") and role_id:
        from src.models.project_allocation_model import ProjectAllocation

        ids = []
        for alloc in ProjectAllocation.query.all():
            members = alloc.members or []
            for member in members:
                if match_allocation_member(member, role, role_id):
                    ids.append(alloc.project_id)
                    break
        return list(dict.fromkeys(ids))
    return []


def iter_task_assignees(task):
    """Yield assignee dicts; supports legacy worker_ids as bare integers."""
    raw = task.worker_ids if task.worker_ids else task.members or []
    if not raw:
        return
    for item in raw:
        if isinstance(item, dict):
            yield item
        elif isinstance(item, (int, float)):
            i = int(item)
            yield {"role_id": i, "user_id": i, "role": "worker"}
        elif isinstance(item, str) and str(item).strip().isdigit():
            i = int(str(item).strip())
            yield {"role_id": i, "user_id": i, "role": "worker"}


def task_assigned_to_user(task, role, role_id):
    """Workers only see tasks they are assigned to; TL/admin scope is project-level."""
    role = normalize_role_name(role)
    if role not in ("worker",):
        return True
    if role_id is None:
        return False
    for member in iter_task_assignees(task):
        mid = member_record_id(member)
        if mid is not None and int(mid) == int(role_id):
            return True
    return False


def filter_tasks_for_user(tasks, role, role_id):
    if normalize_role_name(role) != "worker":
        return tasks
    return [t for t in tasks if task_assigned_to_user(t, role, role_id)]
