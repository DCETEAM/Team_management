"""Find existing SQLAlchemy models by table name; no model import paths are assumed."""
def get_models_by_table(db):
    found = {}
    try:
        mappers = list(db.Model.registry.mappers)
    except Exception as exc:
        raise RuntimeError(
            "Could not inspect SQLAlchemy model registry. Ensure all model modules "
            "are imported before registering the task-chat blueprint."
        ) from exc

    for mapper in mappers:
        model = mapper.class_
        table_name = getattr(model, "__tablename__", None)
        if table_name:
            found[table_name] = model
    return found


def require_models(db):
    models = get_models_by_table(db)
    required = [
        "tasks", "task_statuses", "task_status_history", "task_comments",
        "sub_tasks", "projects", "project_allocations", "workers", "admins"
    ]
    missing = [name for name in required if name not in models]
    if missing:
        raise RuntimeError(
            "These SQLAlchemy models are not registered/imported: "
            + ", ".join(missing)
            + ". Import your model modules before registering this blueprint."
        )
    return models
