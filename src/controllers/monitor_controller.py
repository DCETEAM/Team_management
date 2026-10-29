import datetime
import secrets
import uuid as uuid_lib
from flask import jsonify, request, g, current_app
from sqlalchemy import and_, func
from src import db
from src.models.user_model import User
from src.models.task_model import Task
from src.models.worker_model import Worker
from src.models.monitor_models import (
    MonitorDevice,
    MonitorPairingCode,
    WorkSession,
    ActivityEvent,
    AppUsageSegment,
    DailyWorkSummary,
    _hash_token,
)
from src.utils.monitor_auth import MONITORED_ROLES, MANAGER_ROLES
from src.utils.monitor_settings import (
    IDLE_THRESHOLD_SECONDS,
    HEARTBEAT_STALE_SECONDS,
    HEARTBEAT_INTERVAL_SECONDS,
    PAIRING_CODE_TTL_MINUTES,
    PAIRING_CODE_GRACE_SECONDS,
)
from src.utils.monitor_client_time import (
    parse_client_datetime,
    get_client_now_from_request,
    get_client_work_date_from_request,
    format_dt_z,
)


def _client_time_error():
    return jsonify(
        {
            "status": 0,
            "msg": "Missing or invalid client time. Send X-Client-Time (ISO-8601) or client_time in the JSON body.",
        }
    ), 400


def _client_date_error():
    return jsonify(
        {
            "status": 0,
            "msg": "Missing client date. Use ?date=YYYY-MM-DD or send X-Client-Local-Date / X-Client-Time headers.",
        }
    ), 400


def _require_client_now():
    dt = get_client_now_from_request(request)
    if not dt:
        return None, _client_time_error()
    return dt, None


def _require_client_work_date():
    d = get_client_work_date_from_request(request)
    if not d:
        return None, _client_date_error()
    return d, None


def _parse_dt(val):
    return parse_client_datetime(val)


def _iso(dt):
    return format_dt_z(dt)


def _normalize_pairing_code(raw):
    if raw is None:
        return ""
    return str(raw).strip().replace(" ", "").replace("-", "").upper()


def _pairing_expired(expires_at, now):
    if not expires_at or not now:
        return True
    grace = datetime.timedelta(seconds=PAIRING_CODE_GRACE_SECONDS)
    return expires_at + grace < now


def _invalidate_user_pairing_codes(user_id, now):
    (
        MonitorPairingCode.query.filter(
            MonitorPairingCode.user_id == user_id,
            MonitorPairingCode.used_at.is_(None),
        ).update({MonitorPairingCode.used_at: now}, synchronize_session=False)
    )


def _user_display(user):
    if not user:
        return None
    person = None
    if user.role in ("superadmin", "admin", "scrum"):
        from src.models.admin_model import Admin

        person = Admin.query.get(user.role_id)
    elif user.role in ("team_leader", "worker"):
        person = Worker.query.get(user.role_id)
    name = ""
    if person:
        name = f"{person.first_name or ''} {person.last_name or ''}".strip()
    return {"user_id": user.id, "email": user.email, "role": user.role, "name": name}


def _task_allowed_for_user(user, task_id):
    if not task_id:
        return True
    task = Task.query.get(task_id)
    if not task:
        return False
    members = task.members or task.worker_ids or []
    for m in members:
        if isinstance(m, dict):
            rid = m.get("role_id") or m.get("user_id")
            if rid == user.role_id:
                return True
        elif m == user.role_id:
            return True
    return user.role in ("superadmin", "admin", "scrum")


def _session_owned(session, device, user):
    return session.device_id == device.id and session.user_id == user.id


def _upsert_daily_summary(user_id, work_date, deltas, generated_at):
    row = DailyWorkSummary.query.filter_by(user_id=user_id, work_date=work_date).first()
    if not row:
        row = DailyWorkSummary(user_id=user_id, work_date=work_date)
        db.session.add(row)
    row.tracked_seconds = (row.tracked_seconds or 0) + deltas.get("tracked", 0)
    row.active_seconds = (row.active_seconds or 0) + deltas.get("active", 0)
    row.idle_seconds = (row.idle_seconds or 0) + deltas.get("idle", 0)
    row.break_seconds = (row.break_seconds or 0) + deltas.get("break", 0)
    row.generated_at = generated_at


def get_monitor_policy(decoded_payload=None):
    return jsonify(
        {
            "status": 1,
            "policy": {
                "idle_threshold_seconds": IDLE_THRESHOLD_SECONDS,
                "heartbeat_interval_seconds": HEARTBEAT_INTERVAL_SECONDS,
                "capture_foreground_apps": True,
                "allowed_metadata_only": True,
                "no_keystrokes": True,
                "no_screen_capture": True,
            },
        }
    ), 200


def create_pairing_code(decoded_payload=None):
    user_id = decoded_payload.get("user_id")
    user = User.query.get(user_id)
    if not user or not user.is_active or user.role not in MONITORED_ROLES:
        return jsonify({"status": 0, "msg": "Monitoring is not available for this account"}), 403
    now, err = _require_client_now()
    if err:
        return err
    _invalidate_user_pairing_codes(user_id, now)
    code = secrets.token_hex(3).upper()
    expires = now + datetime.timedelta(minutes=PAIRING_CODE_TTL_MINUTES)
    row = MonitorPairingCode(user_id=user_id, code=code, expires_at=expires)
    db.session.add(row)
    db.session.commit()
    return jsonify(
        {
            "status": 1,
            "pairing_code": code,
            "expires_at": _iso(expires),
        }
    ), 200


def register_device():
    data = request.get_json() or {}
    pairing_code = _normalize_pairing_code(data.get("pairing_code"))
    device_uuid = (data.get("device_uuid") or "").strip()
    if not pairing_code or not device_uuid:
        return jsonify({"status": 0, "msg": "pairing_code and device_uuid required"}), 400

    now, err = _require_client_now()
    if err:
        return err

    pair = (
        MonitorPairingCode.query.filter_by(code=pairing_code)
        .order_by(MonitorPairingCode.id.desc())
        .first()
    )
    if not pair:
        return jsonify(
            {
                "status": 0,
                "msg": "Pairing code not found. In the web app open Activity Monitor, click Generate pairing code, then enter the new code here.",
            }
        ), 400
    if pair.used_at is not None:
        return jsonify(
            {
                "status": 0,
                "msg": "This pairing code was already used. Generate a new code on Activity Monitor and try again.",
            }
        ), 400
    if _pairing_expired(pair.expires_at, now):
        return jsonify(
            {
                "status": 0,
                "msg": "Pairing code expired. Generate a new code on Activity Monitor (valid for "
                f"{PAIRING_CODE_TTL_MINUTES} minutes).",
            }
        ), 400

    existing = MonitorDevice.query.filter_by(device_uuid=device_uuid).first()
    plain_token = MonitorDevice.generate_token()
    if existing:
        if existing.user_id != pair.user_id:
            return jsonify({"status": 0, "msg": "Device already registered to another user"}), 409
        existing.token_hash = _hash_token(plain_token)
        existing.device_name = data.get("device_name") or existing.device_name
        existing.operating_system = data.get("operating_system") or existing.operating_system
        existing.agent_version = data.get("agent_version") or existing.agent_version
        existing.status = "active"
        existing.last_seen_at = now
        device = existing
    else:
        device = MonitorDevice(
            user_id=pair.user_id,
            device_uuid=device_uuid,
            device_name=data.get("device_name"),
            operating_system=data.get("operating_system"),
            agent_version=data.get("agent_version"),
            token_hash=_hash_token(plain_token),
            status="active",
            last_seen_at=now,
        )
        db.session.add(device)

    pair.used_at = now
    db.session.commit()
    return jsonify(
        {
            "status": 1,
            "device_id": device.id,
            "device_uuid": device.device_uuid,
            "device_token": plain_token,
            "user": _user_display(User.query.get(pair.user_id)),
        }
    ), 200


def start_session():
    device = g.monitor_device
    user = g.monitor_user
    data = request.get_json() or {}
    task_id = data.get("task_id")
    if task_id is not None:
        try:
            task_id = int(task_id)
        except (TypeError, ValueError):
            return jsonify({"status": 0, "msg": "Invalid task_id"}), 400
        if not _task_allowed_for_user(user, task_id):
            return jsonify({"status": 0, "msg": "Task not assigned to you"}), 403

    open_sess = (
        WorkSession.query.filter_by(user_id=user.id, device_id=device.id)
        .filter(WorkSession.ended_at.is_(None))
        .order_by(WorkSession.started_at.desc())
        .first()
    )
    if open_sess:
        return jsonify({"status": 1, "session": _serialize_session(open_sess), "resumed": True}), 200

    now, err = _require_client_now()
    if err:
        return err
    sess = WorkSession(
        user_id=user.id,
        device_id=device.id,
        task_id=task_id,
        started_at=now,
        last_heartbeat_at=now,
        status="active",
    )
    db.session.add(sess)
    device.last_seen_at = now
    db.session.commit()
    return jsonify({"status": 1, "session": _serialize_session(sess)}), 201


def _serialize_session(sess):
    return {
        "id": sess.id,
        "user_id": sess.user_id,
        "device_id": sess.device_id,
        "task_id": sess.task_id,
        "started_at": _iso(sess.started_at),
        "ended_at": _iso(sess.ended_at),
        "last_heartbeat_at": _iso(sess.last_heartbeat_at),
        "status": sess.status,
        "active_seconds": sess.active_seconds,
        "idle_seconds": sess.idle_seconds,
        "break_seconds": sess.break_seconds,
    }


def session_heartbeat(session_id):
    device = g.monitor_device
    user = g.monitor_user
    sess = WorkSession.query.get(session_id)
    if not sess or not _session_owned(sess, device, user):
        return jsonify({"status": 0, "msg": "Session not found"}), 404
    if sess.ended_at:
        return jsonify({"status": 0, "msg": "Session ended"}), 400

    data = request.get_json() or {}
    received_at, err = _require_client_now()
    if err:
        return err
    work_date, err = _require_client_work_date()
    if err:
        return err
    active_delta = max(0, int(data.get("active_seconds_delta") or 0))
    idle_delta = max(0, int(data.get("idle_seconds_delta") or 0))
    break_delta = max(0, int(data.get("break_seconds_delta") or 0))
    client_state = (data.get("client_state") or "unknown").lower()

    if client_state in ("active", "idle", "locked", "break", "offline", "unknown"):
        sess.status = client_state if client_state != "unknown" else sess.status

    sess.active_seconds = (sess.active_seconds or 0) + active_delta
    sess.idle_seconds = (sess.idle_seconds or 0) + idle_delta
    sess.break_seconds = (sess.break_seconds or 0) + break_delta
    sess.last_heartbeat_at = received_at
    device.last_seen_at = received_at

    _upsert_daily_summary(
        user.id,
        work_date,
        {
            "tracked": active_delta + idle_delta + break_delta,
            "active": active_delta,
            "idle": idle_delta,
            "break": break_delta,
        },
        received_at,
    )
    db.session.commit()
    return jsonify(
        {
            "status": 1,
            "received_at": _iso(received_at),
            "session": _serialize_session(sess),
            "idle_threshold_seconds": IDLE_THRESHOLD_SECONDS,
        }
    ), 200


def session_events(session_id):
    device = g.monitor_device
    user = g.monitor_user
    sess = WorkSession.query.get(session_id)
    if not sess or not _session_owned(sess, device, user):
        return jsonify({"status": 0, "msg": "Session not found"}), 404

    data = request.get_json() or {}
    events = data.get("events") or []
    if isinstance(data.get("event"), dict):
        events = [data["event"]]

    now, err = _require_client_now()
    if err:
        return err

    created = 0
    for ev in events:
        event_uuid = (ev.get("event_uuid") or "").strip() or str(uuid_lib.uuid4())
        if ActivityEvent.query.filter_by(event_uuid=event_uuid).first():
            continue
        occurred_at = _parse_dt(ev.get("occurred_at")) or now
        row = ActivityEvent(
            event_uuid=event_uuid,
            session_id=sess.id,
            event_type=(ev.get("event_type") or "unknown")[:50],
            occurred_at=occurred_at,
            metadata_json=ev.get("metadata"),
        )
        db.session.add(row)
        created += 1

        apps = ev.get("app_segments") or []
        for seg in apps:
            started_at = _parse_dt(seg.get("started_at")) or now
            ended_raw = seg.get("ended_at")
            db.session.add(
                AppUsageSegment(
                    session_id=sess.id,
                    app_category=(seg.get("app_category") or "unknown")[:100],
                    app_name=(seg.get("app_name") or None),
                    started_at=started_at,
                    ended_at=_parse_dt(ended_raw) if ended_raw else None,
                    duration_seconds=max(0, int(seg.get("duration_seconds") or 0)),
                )
            )

    device.last_seen_at = now
    db.session.commit()
    return jsonify({"status": 1, "created": created}), 200


def session_break_start(session_id):
    return _set_session_status(session_id, "break")


def session_break_end(session_id):
    return _set_session_status(session_id, "active")


def _set_session_status(session_id, status):
    device = g.monitor_device
    user = g.monitor_user
    sess = WorkSession.query.get(session_id)
    if not sess or not _session_owned(sess, device, user):
        return jsonify({"status": 0, "msg": "Session not found"}), 404
    now, err = _require_client_now()
    if err:
        return err
    sess.status = status
    sess.last_heartbeat_at = now
    device.last_seen_at = now
    db.session.commit()
    return jsonify({"status": 1, "session": _serialize_session(sess)}), 200


def end_session(session_id):
    device = g.monitor_device
    user = g.monitor_user
    sess = WorkSession.query.get(session_id)
    if not sess or not _session_owned(sess, device, user):
        return jsonify({"status": 0, "msg": "Session not found"}), 404
    now, err = _require_client_now()
    if err:
        return err
    sess.ended_at = now
    sess.status = "ended"
    sess.last_heartbeat_at = now
    device.last_seen_at = now
    db.session.commit()
    return jsonify({"status": 1, "session": _serialize_session(sess)}), 200


def me_today(decoded_payload=None):
    user_id = decoded_payload.get("user_id")
    today, err = _require_client_work_date()
    if err:
        return err
    summary = _effective_daily_summary(user_id, today, today)
    open_sess = (
        WorkSession.query.filter_by(user_id=user_id)
        .filter(WorkSession.ended_at.is_(None))
        .order_by(WorkSession.started_at.desc())
        .first()
    )
    return jsonify(
        {
            "status": 1,
            "date": today.isoformat(),
            "summary": summary or _empty_summary(),
            "open_session": _serialize_session(open_sess) if open_sess else None,
        }
    ), 200


def _serialize_summary(row):
    if not row:
        return None
    active = row.active_seconds or 0
    idle = row.idle_seconds or 0
    br = row.break_seconds or 0
    tracked = row.tracked_seconds or 0
    if tracked < active + idle + br:
        tracked = active + idle + br
    return {
        "tracked_seconds": tracked,
        "active_seconds": active,
        "idle_seconds": idle,
        "break_seconds": br,
        "tasks_completed": row.tasks_completed,
    }


def _summary_from_open_session(sess):
    if not sess:
        return None
    active = sess.active_seconds or 0
    idle = sess.idle_seconds or 0
    br = sess.break_seconds or 0
    return {
        "tracked_seconds": active + idle + br,
        "active_seconds": active,
        "idle_seconds": idle,
        "break_seconds": br,
        "tasks_completed": 0,
    }


def _merge_summary_dicts(stored, live):
    if not stored and not live:
        return None
    if not stored:
        return live
    if not live:
        return stored
    out = dict(stored)
    for key in ("tracked_seconds", "active_seconds", "idle_seconds", "break_seconds"):
        out[key] = max(out.get(key) or 0, live.get(key) or 0)
    out["tracked_seconds"] = max(
        out.get("tracked_seconds") or 0,
        (out.get("active_seconds") or 0)
        + (out.get("idle_seconds") or 0)
        + (out.get("break_seconds") or 0),
    )
    return out


def _effective_daily_summary(user_id, work_date, client_work_date):
    row = DailyWorkSummary.query.filter_by(user_id=user_id, work_date=work_date).first()
    stored = _serialize_summary(row)
    open_sess = (
        WorkSession.query.filter_by(user_id=user_id)
        .filter(WorkSession.ended_at.is_(None))
        .order_by(WorkSession.started_at.desc())
        .first()
    )
    if client_work_date and client_work_date == work_date and open_sess:
        live = _summary_from_open_session(open_sess)
        return _merge_summary_dicts(stored, live)
    return stored


def _sessions_for_work_date(user_id, work_date, client_work_date):
    sessions = (
        WorkSession.query.filter_by(user_id=user_id)
        .filter(func.date(WorkSession.started_at) == work_date)
        .order_by(WorkSession.started_at.asc())
        .all()
    )
    if client_work_date and client_work_date == work_date:
        open_sess = (
            WorkSession.query.filter_by(user_id=user_id)
            .filter(WorkSession.ended_at.is_(None))
            .order_by(WorkSession.started_at.desc())
            .first()
        )
        if open_sess and all(s.id != open_sess.id for s in sessions):
            sessions = list(sessions) + [open_sess]
            sessions.sort(key=lambda s: s.started_at or datetime.datetime.min)
    return sessions


def _empty_summary():
    return {
        "tracked_seconds": 0,
        "active_seconds": 0,
        "idle_seconds": 0,
        "break_seconds": 0,
        "tasks_completed": 0,
    }


def _live_state_for_session(sess, device, reference_now):
    if not sess or sess.ended_at:
        return "offline"
    if not sess.last_heartbeat_at:
        return "unknown"
    if not reference_now:
        return "unknown"
    age = (reference_now - sess.last_heartbeat_at).total_seconds()
    if age > HEARTBEAT_STALE_SECONDS:
        return "unknown"
    return sess.status or "unknown"


def manager_live(decoded_payload=None):
    ref_now, err = _require_client_now()
    if err:
        return err
    users = (
        User.query.filter(User.is_active.is_(True))
        .filter(User.role.in_(list(MONITORED_ROLES)))
        .order_by(User.id.asc())
        .all()
    )
    results = []
    for u in users:
        sess = (
            WorkSession.query.filter_by(user_id=u.id)
            .filter(WorkSession.ended_at.is_(None))
            .order_by(WorkSession.started_at.desc())
            .first()
        )
        device = MonitorDevice.query.filter_by(user_id=u.id, status="active").order_by(
            MonitorDevice.last_seen_at.desc()
        ).first()
        state = _live_state_for_session(sess, device, ref_now)
        duration = 0
        if sess and sess.started_at:
            duration = int((ref_now - sess.started_at).total_seconds())
        results.append(
            {
                "employee": _user_display(u),
                "live_state": state,
                "session_id": sess.id if sess else None,
                "session_duration_seconds": duration,
                "last_heartbeat_at": _iso(sess.last_heartbeat_at) if sess and sess.last_heartbeat_at else None,
                "device_last_seen_at": _iso(device.last_seen_at) if device and device.last_seen_at else None,
            }
        )
    return jsonify({"status": 1, "employees": results, "as_of": _iso(ref_now)}), 200


def manager_timeline(decoded_payload=None, employee_id=None):
    try:
        employee_id = int(employee_id)
    except (TypeError, ValueError):
        return jsonify({"status": 0, "msg": "Invalid employee id"}), 400
    day = request.args.get("date")
    if not day:
        work_date, err = _require_client_work_date()
        if err:
            return err
    else:
        try:
            work_date = datetime.datetime.strptime(day, "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"status": 0, "msg": "Invalid date"}), 400
        day = work_date.isoformat()

    sessions = (
        WorkSession.query.filter_by(user_id=employee_id)
        .filter(func.date(WorkSession.started_at) == work_date)
        .order_by(WorkSession.started_at.asc())
        .all()
    )
    out = []
    for s in sessions:
        events = ActivityEvent.query.filter_by(session_id=s.id).order_by(
            ActivityEvent.occurred_at.asc()
        ).limit(500).all()
        out.append(
            {
                "session": _serialize_session(s),
                "events": [
                    {
                        "event_uuid": e.event_uuid,
                        "event_type": e.event_type,
                        "occurred_at": _iso(e.occurred_at),
                        "metadata": e.metadata_json,
                    }
                    for e in events
                ],
            }
        )
    return jsonify({"status": 1, "user_id": employee_id, "date": day, "timeline": out}), 200


def manager_daily_report(decoded_payload=None):
    day = request.args.get("date")
    user_filter = request.args.get("user_id")
    if not day:
        work_date, err = _require_client_work_date()
        if err:
            return err
        day = work_date.isoformat()
    else:
        try:
            work_date = datetime.datetime.strptime(day, "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"status": 0, "msg": "Invalid date"}), 400

    q = DailyWorkSummary.query.filter_by(work_date=work_date)
    if user_filter:
        q = q.filter_by(user_id=int(user_filter))
    rows = q.all()
    return jsonify(
        {
            "status": 1,
            "date": day,
            "summaries": [
                {
                    "user_id": r.user_id,
                    "tracked_seconds": r.tracked_seconds,
                    "active_seconds": r.active_seconds,
                    "idle_seconds": r.idle_seconds,
                    "break_seconds": r.break_seconds,
                    "tasks_completed": r.tasks_completed,
                }
                for r in rows
            ],
        }
    ), 200


def revoke_my_devices(decoded_payload=None):
    """Remove active pairings for this user (logout / fresh login). Ends open sessions."""
    user_id = decoded_payload.get("user_id")
    now, err = _require_client_now()
    if err:
        return err
    _invalidate_user_pairing_codes(user_id, now)
    devices = MonitorDevice.query.filter_by(user_id=user_id, status="active").all()
    removed = 0
    for device in devices:
        open_sessions = (
            WorkSession.query.filter_by(device_id=device.id, user_id=user_id)
            .filter(WorkSession.ended_at.is_(None))
            .all()
        )
        for sess in open_sessions:
            sess.ended_at = now
            sess.status = "ended"
            sess.last_heartbeat_at = now
        device.status = "revoked"
        device.token_hash = _hash_token(secrets.token_urlsafe(32))
        removed += 1
    db.session.commit()
    return jsonify({"status": 1, "removed": removed, "revoked": removed}), 200


def _can_view_user_analytics(viewer_payload, target_user_id):
    viewer_id = viewer_payload.get("user_id")
    role = viewer_payload.get("role")
    if viewer_id == target_user_id:
        return True
    return role in MANAGER_ROLES


def _users_for_analytics(viewer_payload):
    role = viewer_payload.get("role")
    q = User.query.filter(User.is_active.is_(True)).filter(
        User.role.in_(list(MONITORED_ROLES))
    )
    if role not in MANAGER_ROLES:
        q = q.filter(User.id == viewer_payload.get("user_id"))
    return q.order_by(User.id.asc()).all()


def analytics_overview(decoded_payload=None):
    day = request.args.get("date")
    if not day:
        work_date, err = _require_client_work_date()
        if err:
            return err
        day = work_date.isoformat()
    else:
        try:
            work_date = datetime.datetime.strptime(day, "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"status": 0, "msg": "Invalid date"}), 400

    ref_now = get_client_now_from_request(request)
    client_work_date = get_client_work_date_from_request(request)

    users = _users_for_analytics(decoded_payload)

    rows = []
    totals = {
        "tracked_seconds": 0,
        "active_seconds": 0,
        "idle_seconds": 0,
        "break_seconds": 0,
    }
    for u in users:
        summ = _effective_daily_summary(u.id, work_date, client_work_date) or _empty_summary()
        for k in ("tracked_seconds", "active_seconds", "idle_seconds", "break_seconds"):
            totals[k] += summ.get(k) or 0

        open_sess = (
            WorkSession.query.filter_by(user_id=u.id)
            .filter(WorkSession.ended_at.is_(None))
            .order_by(WorkSession.started_at.desc())
            .first()
        )
        device = MonitorDevice.query.filter_by(user_id=u.id, status="active").first()
        rows.append(
            {
                "user": _user_display(u),
                "summary": summ,
                "live_state": _live_state_for_session(open_sess, device, ref_now),
                "last_heartbeat_at": _iso(open_sess.last_heartbeat_at)
                if open_sess and open_sess.last_heartbeat_at
                else None,
            }
        )

    return jsonify(
        {
            "status": 1,
            "date": day,
            "client_work_date": client_work_date.isoformat() if client_work_date else None,
            "totals": totals,
            "users": rows,
            "viewer_is_manager": decoded_payload.get("role") in MANAGER_ROLES,
        }
    ), 200


def analytics_user_insight(decoded_payload=None, user_id=None):
    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        return jsonify({"status": 0, "msg": "Invalid user id"}), 400
    if not _can_view_user_analytics(decoded_payload, user_id):
        return jsonify({"status": 0, "msg": "Not allowed to view this user"}), 403

    target = User.query.get(user_id)
    if not target or target.role not in MONITORED_ROLES:
        return jsonify({"status": 0, "msg": "User not found"}), 404

    day = request.args.get("date")
    if not day:
        work_date, err = _require_client_work_date()
        if err:
            return err
        day = work_date.isoformat()
    else:
        try:
            work_date = datetime.datetime.strptime(day, "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"status": 0, "msg": "Invalid date"}), 400

    summary = _effective_daily_summary(
        user_id, work_date, get_client_work_date_from_request(request)
    )
    client_work_date = get_client_work_date_from_request(request)
    sessions = _sessions_for_work_date(user_id, work_date, client_work_date)

    timeline = []
    for s in sessions:
        events = (
            ActivityEvent.query.filter_by(session_id=s.id)
            .order_by(ActivityEvent.occurred_at.asc())
            .limit(500)
            .all()
        )
        timeline.append(
            {
                "session": _serialize_session(s),
                "events": [
                    {
                        "event_uuid": e.event_uuid,
                        "event_type": e.event_type,
                        "occurred_at": _iso(e.occurred_at),
                        "metadata": e.metadata_json,
                    }
                    for e in events
                ],
            }
        )

    app_usage = []
    for sess in sessions:
        for seg in AppUsageSegment.query.filter_by(session_id=sess.id).all():
            app_usage.append(
                {
                    "app_name": seg.app_name,
                    "app_category": seg.app_category,
                    "duration_seconds": seg.duration_seconds,
                    "started_at": _iso(seg.started_at) if seg.started_at else None,
                }
            )

    return jsonify(
        {
            "status": 1,
            "date": day,
            "user": _user_display(target),
            "summary": summary or _empty_summary(),
            "sessions": [_serialize_session(s) for s in sessions],
            "app_usage": app_usage,
            "timeline": timeline,
        }
    ), 200
