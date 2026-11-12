from flask import jsonify, request

from src import db
from src.models.project_credential_model import ProjectCredential
from src.models.project_model import Project
from src.utils.allocation_utils import accessible_project_ids
from src.utils.credential_crypto import decrypt_secret, encrypt_secret


def _can_access_project(project_id, decoded_payload):
    allowed = accessible_project_ids(decoded_payload)
    if allowed is None:
        return True
    try:
        pid = int(project_id)
    except (TypeError, ValueError):
        return False
    return pid in allowed


def _serialize(row, include_password=False):
    data = {
        "id": row.id,
        "project_id": row.project_id,
        "label": row.label,
        "username": row.username,
        "notes": row.notes,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }
    if include_password:
        data["password"] = decrypt_secret(row.password_encrypted)
    else:
        data["has_password"] = bool(row.password_encrypted)
    return data


def list_project_credentials(decoded_payload=None):
    try:
        project_id = request.args.get("project_id", type=int)
        if not project_id:
            return jsonify({"msg": "project_id is required", "status": 0}), 400
        if not Project.query.get(project_id):
            return jsonify({"msg": "Project not found", "status": 0}), 404
        if not _can_access_project(project_id, decoded_payload):
            return jsonify({"msg": "Forbidden", "status": 0}), 403

        rows = (
            ProjectCredential.query.filter_by(project_id=project_id)
            .order_by(ProjectCredential.label.asc())
            .all()
        )
        return jsonify(
            {
                "status": 1,
                "credentials": [_serialize(r, include_password=True) for r in rows],
            }
        ), 200
    except Exception as e:
        return jsonify({"msg": str(e), "status": 0}), 500


def create_project_credential(decoded_payload=None):
    try:
        data = request.get_json() or {}
        project_id = data.get("project_id")
        label = (data.get("label") or "").strip()
        username = (data.get("username") or "").strip()
        password = data.get("password")
        notes = (data.get("notes") or "").strip() or None

        if not project_id or not label or not username or password is None:
            return jsonify({"msg": "project_id, label, username and password are required", "status": 0}), 400

        if not Project.query.get(project_id):
            return jsonify({"msg": "Project not found", "status": 0}), 404
        if not _can_access_project(project_id, decoded_payload):
            return jsonify({"msg": "Forbidden", "status": 0}), 403

        if ProjectCredential.query.filter_by(project_id=project_id, label=label).first():
            return jsonify({"msg": f"Credential '{label}' already exists for this project", "status": 0}), 409

        row = ProjectCredential(
            project_id=project_id,
            label=label,
            username=username,
            password_encrypted=encrypt_secret(str(password)),
            notes=notes,
            created_by_role_id=decoded_payload.get("role_id") or decoded_payload.get("roleId"),
            created_by_role=(decoded_payload.get("role") or "").strip().lower(),
        )
        db.session.add(row)
        db.session.commit()
        return jsonify(
            {"status": 1, "msg": "Credential saved", "credential": _serialize(row, include_password=True)}
        ), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": str(e), "status": 0}), 500


def update_project_credential(credential_id, decoded_payload=None):
    try:
        row = ProjectCredential.query.get(credential_id)
        if not row:
            return jsonify({"msg": "Not found", "status": 0}), 404
        if not _can_access_project(row.project_id, decoded_payload):
            return jsonify({"msg": "Forbidden", "status": 0}), 403

        data = request.get_json() or {}
        if "label" in data:
            label = (data["label"] or "").strip()
            if label and label != row.label:
                clash = ProjectCredential.query.filter_by(project_id=row.project_id, label=label).first()
                if clash and clash.id != row.id:
                    return jsonify({"msg": "Label already exists", "status": 0}), 409
                row.label = label
        if "username" in data:
            row.username = (data["username"] or "").strip() or row.username
        if "password" in data and data["password"] is not None and str(data["password"]) != "":
            row.password_encrypted = encrypt_secret(str(data["password"]))
        if "notes" in data:
            row.notes = (data["notes"] or "").strip() or None

        db.session.commit()
        return jsonify({"status": 1, "credential": _serialize(row, include_password=True)}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": str(e), "status": 0}), 500


def delete_project_credential(credential_id, decoded_payload=None):
    try:
        row = ProjectCredential.query.get(credential_id)
        if not row:
            return jsonify({"msg": "Not found", "status": 0}), 404
        if not _can_access_project(row.project_id, decoded_payload):
            return jsonify({"msg": "Forbidden", "status": 0}), 403
        db.session.delete(row)
        db.session.commit()
        return jsonify({"status": 1, "msg": "Deleted"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": str(e), "status": 0}), 500
