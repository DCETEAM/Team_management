"""Profile completion scoring for onboarding wizard."""


def _filled(val):
    if val is None:
        return False
    if isinstance(val, str):
        return bool(val.strip())
    return True


def profile_field_groups(is_worker_side):
    """Same savable fields as AdminForm / WorkerForm (excluding role_type)."""
    if is_worker_side:
        personal = [
            ("first_name", "First name"),
            ("last_name", "Last name"),
            ("email", "Email"),
            ("phone", "Phone"),
            ("avatar_url", "Profile photo"),
        ]
        professional = [
            ("job_title", "Job title"),
            ("department", "Department"),
            ("employment_type", "Employment type"),
            ("joining_date", "Joining date"),
            ("experience_years", "Experience"),
            ("working_hours", "Working hours"),
            ("work_mode", "Work mode"),
            ("status", "Status"),
            ("office_location", "Office location"),
        ]
        extras = [
            ("linkedin_url", "LinkedIn"),
            ("github_url", "GitHub"),
            ("portfolio_url", "Portfolio"),
            ("address_line1", "Address line 1"),
            ("address_line2", "Address line 2"),
            ("city", "City"),
            ("state", "State"),
            ("country", "Country"),
            ("pincode", "Pincode"),
            ("remark", "Notes"),
        ]
    else:
        personal = [
            ("first_name", "First name"),
            ("last_name", "Last name"),
            ("email", "Email"),
            ("phone", "Phone"),
            ("avatar_url", "Profile photo"),
            ("joining_date", "Joining date"),
        ]
        professional = [
            ("experience_years", "Experience"),
            ("working_hours", "Working hours"),
            ("work_mode", "Work mode"),
            ("status", "Status"),
            ("linkedin_url", "LinkedIn"),
            ("office_location", "Office location"),
        ]
        extras = [
            ("address_line1", "Address line 1"),
            ("address_line2", "Address line 2"),
            ("city", "City"),
            ("state", "State"),
            ("country", "Country"),
            ("pincode", "Pincode"),
            ("remark", "Notes"),
        ]
    groups = [
        (0, personal),
        (1, professional),
        (2, extras),
    ]
    return groups


def person_get_field(person, key):
    if not person:
        return None
    val = getattr(person, key, None)
    if key in ("work_mode", "status", "employment_type") and val is not None:
        val = val.value if hasattr(val, "value") else val
    if key == "experience_years" and val is not None:
        try:
            return val if float(val) > 0 else None
        except (TypeError, ValueError):
            return None
    if key == "working_hours" and val is not None:
        try:
            return val if int(val) > 0 else None
        except (TypeError, ValueError):
            return None
    return val


def compute_profile_completion(person, role):
    is_worker_side = role in ("team_leader", "worker")
    groups = profile_field_groups(is_worker_side)
    fields_detail = []
    filled_count = 0
    total = 0
    steps = {0: {"filled": 0, "total": 0}, 1: {"filled": 0, "total": 0}, 2: {"filled": 0, "total": 0}}

    seen_keys = set()
    for step_idx, field_list in groups:
        for key, label in field_list:
            if key in seen_keys:
                continue
            seen_keys.add(key)
            total += 1
            steps[step_idx]["total"] += 1
            ok = _filled(person_get_field(person, key))
            if ok:
                filled_count += 1
                steps[step_idx]["filled"] += 1
            fields_detail.append(
                {"key": key, "label": label, "step": step_idx + 1, "filled": ok}
            )

    percent = round((filled_count / total) * 100) if total else 100
    step_progress = [
        {
            "step": i + 1,
            "percent": round((steps[i]["filled"] / steps[i]["total"]) * 100)
            if steps[i]["total"]
            else 100,
            "filled": steps[i]["filled"],
            "total": steps[i]["total"],
        }
        for i in range(3)
    ]
    return {
        "percent": percent,
        "filled_count": filled_count,
        "total_count": total,
        "fields": fields_detail,
        "steps": step_progress,
        "is_complete": percent >= 100,
    }
