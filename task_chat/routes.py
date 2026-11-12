from flask import Blueprint, request, jsonify
from .model_registry import require_models
from .date_resolver import local_today
from .payload_service import build_payload
from .retrieval_service import retrieve_tasks
from .response_service import generate_answer
from .ollama_service import OllamaError


def create_task_chat_blueprint(db, url_prefix="/api"):
    bp = Blueprint("task_chat", __name__)

    @bp.post("/task-chat")
    def task_chat():
        body = request.get_json(silent=True) or {}
        prompt = body.get("prompt")
        print(prompt)

        if not isinstance(prompt, str) or not prompt.strip():
            return jsonify({
                "success": False,
                "error": "A non-empty 'prompt' string is required."
            }), 400

        try:
            models = require_models(db)
            today = local_today()
            payload = build_payload(prompt.strip(), today)

            records, resolutions, issue = retrieve_tasks(models, payload, today)
            if issue:
                return jsonify({
                    "success": False,
                    "type": issue["type"],
                    "message": issue["message"],
                    "candidates": issue.get("candidates", []),
                    "interpreted_payload": payload
                }), 200

            answer = generate_answer(
                prompt.strip(), payload, records, resolutions, today
            )

            return jsonify({
                "success": True,
                "answer": answer,
                "interpreted_payload": payload,
                "resolved_names": resolutions,
                "total_records": len(records),
                "data": records
            }), 200

        except (OllamaError, ValueError) as exc:
            return jsonify({"success": False, "error": str(exc)}), 502
        except Exception as exc:
            # Log the full exception in your Flask logger; avoid leaking internals to clients.
            bp.logger.exception("Task-chat request failed")
            return jsonify({
                "success": False,
                "error": "Task-chat processing failed. Check the Flask application logs."
            }), 500

    return bp
