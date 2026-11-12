import json
from .ollama_service import chat


def generate_answer(prompt, payload, records, resolutions, today):
    if payload.get("intent") == "task_count":
        # Count is calculated deterministically from retrieved database records.
        return f"I found {len(records)} matching task(s)."

    system = (
        "You are a task-management assistant. Answer only from the supplied database records. "
        "Do not invent task names, people, dates, statuses, comments or project details. "
        "If no records were found, say so clearly. "
        "Use concise, readable formatting. "
        "Do not expose internal database IDs, passwords, tokens or raw implementation details. "
        "If the records are truncated by the result limit, say that the response may show only a limited set."
    )
    context = {
        "server_local_date": today.isoformat(),
        "interpreted_filters": payload,
        "resolved_names": resolutions,
        "database_records": records
    }
    user = (
        f"User question:\n{prompt}\n\n"
        f"Database context (JSON):\n{json.dumps(context, ensure_ascii=False, default=str)}\n\n"
        "Answer the user's question using this context."
    )
    return chat(
        [{"role": "system", "content": system},
         {"role": "user", "content": user}],
        temperature=0.2
    )
