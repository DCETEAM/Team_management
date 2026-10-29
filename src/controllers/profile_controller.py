from flask import jsonify, request
from src import db
from src.models.user_model import User
from src.models.admin_model import Admin
from src.models.worker_model import Worker
from src.models.project_model import Project
from src.models.project_allocation_model import ProjectAllocation
from src.utils.jwt import decode_jwt_token
from src.utils.date_utils import parse_date, safe_isoformat
from src.utils.profile_completion import compute_profile_completion
from src.utils.role_utils import get_person_details
from src.utils.avatar_utils import apply_avatar_update


def _get_user_from_payload(decoded_payload):
    user_id = decoded_payload.get("user_id")
    return User.query.get(user_id) if user_id else None


def _get_person_record(user):
    if not user:
        return None, None
    if user.role in ("superadmin", "admin", "scrum"):
        return Admin.query.get(user.role_id), "admin"
    if user.role in ("team_leader", "worker"):
        return Worker.query.get(user.role_id), "worker"
    return None, None


def _sync_onboarding_flags(user, *, skipped=None, completed=None):
    if skipped is not None:
        user.profile_onboarding_skipped = bool(skipped)
    if completed is not None:
        user.profile_onboarding_completed = bool(completed)
    person, _kind = _get_person_record(user)
    if person:
        if skipped is not None and hasattr(person, "profile_onboarding_skipped"):
            person.profile_onboarding_skipped = bool(skipped)
        if completed is not None and hasattr(person, "profile_onboarding_completed"):
            person.profile_onboarding_completed = bool(completed)


def _onboarding_flags_payload(user):
    person, _kind = _get_person_record(user)
    skipped = bool(user.profile_onboarding_skipped)
    completed = bool(user.profile_onboarding_completed)
    if person and hasattr(person, "profile_onboarding_skipped"):
        skipped = skipped or bool(person.profile_onboarding_skipped)
    if person and hasattr(person, "profile_onboarding_completed"):
        completed = completed or bool(person.profile_onboarding_completed)
    return skipped, completed


def _enum_value(val):
    if val is None:
        return None
    return val.value if hasattr(val, "value") else val


def _role_type_for_profile(user, person, kind):
    if kind == "worker":
        if user.role == "team_leader" or getattr(person, "is_tl", False):
            return "team_leader"
        return "worker"
    if user.role == "superadmin" or getattr(person, "is_superadmin", False):
        return "superadmin"
    if user.role == "scrum" or getattr(person, "is_scrum", False):
        return "scrum"
    return "admin"


def _serialize_person(person, person_kind, user, role):
    if not person:
        return {}
    base = {
        "first_name": person.first_name,
        "last_name": person.last_name,
        "email": person.email or user.email,
        "phone": person.phone,
        "avatar_url": person.avatar_url,
        "work_mode": _enum_value(getattr(person, "work_mode", None)),
        "office_location": getattr(person, "office_location", None),
        "experience_years": getattr(person, "experience_years", None),
        "linkedin_url": getattr(person, "linkedin_url", None),
        "address_line1": getattr(person, "address_line1", None),
        "address_line2": getattr(person, "address_line2", None),
        "city": getattr(person, "city", None),
        "state": getattr(person, "state", None),
        "country": getattr(person, "country", None),
        "pincode": getattr(person, "pincode", None),
        "joining_date": safe_isoformat(getattr(person, "joining_date", None)),
        "working_hours": getattr(person, "working_hours", None),
        "remark": getattr(person, "remark", None),
        "status": _enum_value(getattr(person, "status", None)) or "ACTIVE",
        "role_type": _role_type_for_profile(user, person, person_kind),
        "role": role,
        "role_id": user.role_id,
    }
    if person_kind == "worker":
        base.update(
            {
                "job_title": person.job_title,
                "department": person.department,
                "github_url": person.github_url,
                "portfolio_url": person.portfolio_url,
                "employment_type": _enum_value(person.employment_type),
                "is_tl": person.is_tl,
            }
        )
    return base


def _role_label(user):
    if user.role == "team_leader":
        return "Team Leader"
    if user.role == "worker":
        return "Worker"
    if user.role == "superadmin":
        return "Super Admin"
    if user.role == "scrum":
        return "Scrum Master"
    return user.role.replace("_", " ").title() if user.role else "User"


def _match_member(member, role, role_id):
    uid = member.get("user_id") if member.get("user_id") is not None else member.get("role_id")
    if uid != role_id:
        return False
    mrole = (member.get("role") or member.get("type") or "").lower()
    if mrole in ("admin", "superadmin", "scrum"):
        return role in ("superadmin", "admin", "scrum")
    if mrole in ("team_leader", "tl"):
        return role == "team_leader"
    if mrole in ("worker",):
        return role == "worker"
    return True


def _get_allocations_for_user(role, role_id):
    allocations = ProjectAllocation.query.all()
    results = []
    for alloc in allocations:
        members = alloc.members or []
        matched = None
        for member in members:
            if _match_member(member, role, role_id):
                matched = member
                break
        if not matched:
            continue
        project = Project.query.get(alloc.project_id)
        if not project:
            continue
        reports_to = None
        parent_id = matched.get("parent_id")
        if parent_id:
            for other in members:
                ouid = other.get("user_id") or other.get("role_id")
                if ouid == parent_id:
                    parent_role = other.get("role") or "team_leader"
                    parent_details = get_person_details(parent_role, parent_id)
                    if parent_details:
                        reports_to = {
                            **parent_details,
                            "display_role": "Team Leader"
                            if parent_role in ("team_leader", "tl")
                            else parent_role,
                        }
                    break
        results.append(
            {
                "project_id": project.id,
                "project_name": project.name,
                "allocation_id": alloc.id,
                "member_role": "Team Leader" if role == "team_leader" else _role_label(
                    type("Obj", (), {"role": role})()
                ),
                "reports_to": reports_to,
                "start_date": safe_isoformat(alloc.start_date),
                "end_date": safe_isoformat(alloc.end_date),
            }
        )
    if role == "team_leader":
        for item in results:
            item["member_role"] = "Team Leader"
    return results


def get_my_profile(decoded_payload=None):
    try:
        user = _get_user_from_payload(decoded_payload)
        if not user:
            return jsonify({"message": "User not found", "status": 0}), 404
        person, kind = _get_person_record(user)
        profile = _serialize_person(person, kind, user, user.role)
        completion = compute_profile_completion(person, user.role)
        allocations = _get_allocations_for_user(user.role, user.role_id)
        skipped, completed = _onboarding_flags_payload(user)
        return jsonify(
            {
                "status": 1,
                "profile": profile,
                "completion": completion,
                "allocations": allocations,
                "profile_onboarding_completed": completed,
                "profile_onboarding_skipped": skipped,
                "role_label": _role_label(user),
            }
        ), 200
    except Exception as e:
        return jsonify({"success": 0, "error": str(e)}), 500


def _apply_profile_update(person, kind, user, data):
    if "first_name" in data and data["first_name"]:
        person.first_name = data["first_name"].strip()
    if "last_name" in data and data["last_name"]:
        person.last_name = data["last_name"].strip()
    if "email" in data and data["email"]:
        new_email = data["email"].strip()
        existing = User.query.filter_by(email=new_email).first()
        if existing and existing.id != user.id:
            raise ValueError(f"User with email '{new_email}' already exists")
        person.email = new_email
        user.email = new_email
    if "phone" in data:
        person.phone = data["phone"].strip() if data["phone"] else None
    if "avatar_url" in data:
        apply_avatar_update(person, data["avatar_url"])
    if "work_mode" in data:
        person.work_mode = data["work_mode"] or None
    if "office_location" in data:
        person.office_location = (
            data["office_location"].strip() if data.get("office_location") else None
        )
    if "experience_years" in data:
        val = data["experience_years"]
        if val == "" or val is None:
            person.experience_years = None
        else:
            try:
                person.experience_years = float(val)
            except (TypeError, ValueError):
                pass
    if "linkedin_url" in data:
        person.linkedin_url = (
            data["linkedin_url"].strip() if data.get("linkedin_url") else None
        )
    for addr_key in (
        "address_line1",
        "address_line2",
        "city",
        "state",
        "country",
        "pincode",
    ):
        if addr_key in data:
            val = data[addr_key]
            setattr(person, addr_key, val.strip() if val else None)
    if "working_hours" in data:
        wh = data["working_hours"]
        person.working_hours = int(wh) if wh not in ("", None) else None
    if "joining_date" in data:
        person.joining_date = parse_date(data["joining_date"])
    if "remark" in data:
        person.remark = data["remark"].strip() if data.get("remark") else None
    if "status" in data and data["status"]:
        person.status = data["status"]
    if kind == "worker":
        if "job_title" in data:
            person.job_title = (
                data["job_title"].strip() if data.get("job_title") else None
            )
        if "department" in data:
            person.department = (
                data["department"].strip() if data.get("department") else None
            )
        if "github_url" in data:
            person.github_url = (
                data["github_url"].strip() if data.get("github_url") else None
            )
        if "portfolio_url" in data:
            person.portfolio_url = (
                data["portfolio_url"].strip() if data.get("portfolio_url") else None
            )
        if "employment_type" in data:
            person.employment_type = data["employment_type"] or None


def update_my_profile(decoded_payload=None):
    try:
        user = _get_user_from_payload(decoded_payload)
        if not user:
            return jsonify({"message": "User not found", "status": 0}), 404
        person, kind = _get_person_record(user)
        if not person:
            return jsonify({"message": "Profile not found", "status": 0}), 404
        data = request.get_json() or {}
        _apply_profile_update(person, kind, user, data)
        db.session.commit()
        completion = compute_profile_completion(person, user.role)
        profile = _serialize_person(person, kind, user, user.role)
        return jsonify(
            {
                "status": 1,
                "message": "Profile updated",
                "profile": profile,
                "completion": completion,
            }
        ), 200
    except Exception as e:
        db.session.rollback()
        if isinstance(e, ValueError):
            return jsonify({"msg": str(e), "status": 0}), 409
        return jsonify({"success": 0, "error": str(e)}), 500


def complete_profile_onboarding(decoded_payload=None):
    try:
        user = _get_user_from_payload(decoded_payload)
        if not user:
            return jsonify({"message": "User not found", "status": 0}), 404
        _sync_onboarding_flags(user, completed=True, skipped=False)
        db.session.commit()
        return jsonify(
            {
                "status": 1,
                "message": "Onboarding marked complete",
                "profile_onboarding_completed": True,
                "profile_onboarding_skipped": False,
            }
        ), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": 0, "error": str(e)}), 500


def skip_profile_onboarding(decoded_payload=None):
    try:
        user = _get_user_from_payload(decoded_payload)
        if not user:
            return jsonify({"message": "User not found", "status": 0}), 404
        _sync_onboarding_flags(user, skipped=True, completed=False)
        db.session.commit()
        return jsonify(
            {
                "status": 1,
                "message": "Onboarding skipped",
                "profile_onboarding_completed": False,
                "profile_onboarding_skipped": True,
            }
        ), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": 0, "error": str(e)}), 500
