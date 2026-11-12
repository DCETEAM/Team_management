from datetime import date
from .ollama_service import chat, extract_json


PAYLOAD_SCHEMA = {
    "intent": "list_tasks | task_summary | task_details | task_count",
    "filters": {
        "user_name": None,
        "user_role": None,
        "task_name": None,
        "project_name": None,
        "status_name": None,
        "priority": None,
        "sprint_name": None,
        "assigned_by_name": None,
        "assigned_by_role": None,
        "start_date": None,
        "end_date": None,
        "date_preset": None
    },
    "include": ["sub_tasks", "comments", "status_history"],
    "sort_by": "due_date | start_date | created_at | priority",
    "sort_order": "asc | desc",
    "limit": 50
}


def build_payload(user_prompt, today):
    system = (
        "You are a strict task-management prompt-to-payload parser. "
        "Return ONLY valid JSON matching the supplied schema. "
        "Do not generate SQL, database IDs, API calls, or explanations. "
        "All person, task, project, sprint and status filters must be readable text names. "
        "Use null for filters not stated or clearly implied. "
        "For relative dates, use date_preset values: today, yesterday, tomorrow, "
        "this_week, last_week, this_month, last_month, overdue, upcoming. "
        "For explicit date ranges use YYYY-MM-DD in start_date and end_date. "
        "For 'today's tasks', use date_preset='today'. "
        "Do not guess a person's full name. "
        "Allowed intents: list_tasks, task_summary, task_details, task_count. "
        "If the user asks for a particular task, use task_details. "
        "If they ask how many/count, use task_count. "
        "If they ask for a general overview, use task_summary. "
        "Otherwise use list_tasks. "
        "Only include supported fields from the schema."
    )
    user = (
        f"Server-local date: {today.isoformat()}\n"
        f"Required JSON schema/example:\n{PAYLOAD_SCHEMA}\n\n"
        f"User request:\n{user_prompt}"
    )
    raw = chat(
        [{"role": "system", "content": system},
         {"role": "user", "content": user}],
        json_mode=True,
        temperature=0
    )
    payload = extract_json(raw)
    if not isinstance(payload, dict):
        raise ValueError("Qwen payload must be a JSON object.")

    payload.setdefault("intent", "list_tasks")
    payload.setdefault("filters", {})
    payload.setdefault("include", ["sub_tasks", "comments", "status_history"])
    payload.setdefault("sort_by", "due_date")
    payload.setdefault("sort_order", "asc")
    payload.setdefault("limit", 50)

    allowed_filters = PAYLOAD_SCHEMA["filters"].keys()
    payload["filters"] = {
        key: payload["filters"].get(key)
        for key in allowed_filters
    }
    payload["intent"] = payload["intent"] if payload["intent"] in {
        "list_tasks", "task_summary", "task_details", "task_count"
    } else "list_tasks"
    payload["limit"] = max(1, min(int(payload.get("limit") or 50), 100))
    payload["sort_order"] = "desc" if payload["sort_order"] == "desc" else "asc"
    if payload["sort_by"] not in {"due_date", "start_date", "created_at", "priority"}:
        payload["sort_by"] = "due_date"
    return payload
