"""Project management flags — keep in sync with frontend projectPermissions.js."""

ADMIN_ROLES = frozenset({"superadmin", "admin", "scrum"})


def normalize_role(role):
    return (role or "").strip().lower()


def is_admin_role(role):
    return normalize_role(role) in ADMIN_ROLES


def can_modify_project_tasks(project, role):
    """Add, edit, delete tasks (matches board canAddEditDelete)."""
    role = normalize_role(role)
    if role not in ("team_leader", "worker"):
        return True
    if not project:
        return False
    if project.company_managed:
        return False
    if project.by_tl_managed:
        return role == "team_leader"
    if project.team_managed:
        return True
    return False


def can_manage_project_sprints(project, role):
    """Create / edit sprints for worker or team leader roles."""
    role = normalize_role(role)
    if role not in ("team_leader", "worker"):
        return True
    if not project:
        return False
    if project.company_managed:
        return False
    return True


def can_move_task_to_status(role, target_status):
    if normalize_role(role) != "worker":
        return True
    if target_status and getattr(target_status, "is_confidential", False):
        return False
    return True


def restriction_message(project, action="This action"):
    if project and project.company_managed:
        return (
            f"{action} is restricted: this project is company managed. "
            "Only administrators can change tasks and sprints."
        )
    if project and project.by_tl_managed:
        return (
            f"{action} is restricted: this project is managed by the team leader. "
            "Workers cannot modify tasks on this project."
        )
    return f"{action} is restricted for your role on this project."
