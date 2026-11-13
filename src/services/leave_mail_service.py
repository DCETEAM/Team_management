import html
from src import db
from src.models.admin_model import Admin
from src.models.leave_mail_user_template_model import LeaveMailUserTemplate
from src.utils.role_utils import get_person_details
from src.controllers.email_controller import send_html_email


def _admin_recipient_row(admin):
    name = f"{admin.first_name or ''} {admin.last_name or ''}".strip()
    role = "superadmin" if admin.is_superadmin else "admin" if admin.is_admin else "scrum" if admin.is_scrum else "admin"
    return {
        "id": admin.id,
        "first_name": admin.first_name,
        "last_name": admin.last_name,
        "email": admin.email,
        "name": name,
        "role_label": role.replace("_", " "),
    }


def list_leave_mail_admins():
    admins = (
        Admin.query.filter(Admin.status == "ACTIVE")
        .filter(Admin.email.isnot(None))
        .filter(Admin.email != "")
        .order_by(Admin.first_name, Admin.last_name)
        .all()
    )
    result = []
    for a in admins:
        if not (a.is_superadmin or a.is_admin or a.is_scrum):
            continue
        result.append(_admin_recipient_row(a))
    return result


def admin_emails_by_ids(admin_ids):
    if not admin_ids:
        return []
    rows = Admin.query.filter(Admin.id.in_(admin_ids)).all()
    by_id = {r.id: r.email.strip() for r in rows if r.email}
    return [by_id[i] for i in admin_ids if i in by_id and by_id[i]]


def admin_by_id(admin_id):
    if not admin_id:
        return None
    return Admin.query.get(admin_id)


def _type_label(leave_type, leave_subtype):
    if leave_type == "permission":
        return "Permission"
    if leave_subtype == "half_day":
        return "Half Day Leave"
    return "Full Day Leave"


def _date_line(leave_payload):
    start = leave_payload.get("start_date") or ""
    end = leave_payload.get("end_date") or start
    line = start if start == end else f"{start} to {end}"
    st = leave_payload.get("start_time")
    et = leave_payload.get("end_time")
    if st and et:
        line += f" ({st} – {et})"
    return line


def get_user_mail_template(role_id, role):
    return LeaveMailUserTemplate.query.filter_by(role_id=role_id, role=role).first()


def save_user_mail_template(role_id, role, subject, body):
    subject = (subject or "").strip()
    body = (body or "").strip()
    if not subject and not body:
        return
    row = get_user_mail_template(role_id, role)
    if not row:
        row = LeaveMailUserTemplate(role_id=role_id, role=role, subject=subject, body=body)
        db.session.add(row)
    else:
        row.subject = subject
        row.body = body
    db.session.commit()


def plain_body_to_html(body_plain):
    text = body_plain or ""
    escaped = html.escape(text)
    br_body = escaped.replace("\r\n", "\n").replace("\n", "<br>\n")
    return f"""<html><body style="font-family:Segoe UI,Arial,sans-serif;padding:20px;color:#0f172a;line-height:1.5;">
<div style="max-width:640px;margin:0 auto;">{br_body}</div>
</body></html>"""


def build_leave_request_plain(requester, leave_payload, to_admin=None):
    requester_name = f"{requester.get('first_name', '')} {requester.get('last_name', '')}".strip()
    requester_email = requester.get("email") or ""
    approver_name = (to_admin or {}).get("name") or "Sir/Madam"
    type_label = _type_label(leave_payload.get("type"), leave_payload.get("leave_subtype"))
    date_line = _date_line(leave_payload)
    reason = leave_payload.get("reason") or ""
    remark = leave_payload.get("remark") or ""

    subject = f"Leave / Permission Request — {requester_name} ({type_label})"

    lines = [
        f"Dear {approver_name},",
        "",
        f"I would like to submit a {type_label} request for your approval.",
        "",
        f"Request type: {type_label}",
        f"Date / time: {date_line}",
        f"Reason: {reason}",
    ]
    if remark:
        lines.append(f"Remark: {remark}")
    lines.extend(
        [
            "",
            "Please review this request in Dce Task Manager (Leave & Permissions).",
            "",
            "Regards,",
            requester_name,
        ]
    )
    if requester_email:
        lines.append(requester_email)

    body = "\n".join(lines)
    return subject, body


def resolve_compose_mail(requester, leave_payload, to_admin_id=None, role_id=None, role=None):
    to_admin = None
    if to_admin_id:
        admin = admin_by_id(to_admin_id)
        if admin:
            to_admin = _admin_recipient_row(admin)
    default_subject, default_body = build_leave_request_plain(requester, leave_payload, to_admin)

    saved = get_user_mail_template(role_id, role) if role_id and role else None
    if saved and (saved.subject or saved.body):
        return {
            "subject": saved.subject or default_subject,
            "body": saved.body or default_body,
            "uses_saved_template": True,
            "default_subject": default_subject,
            "default_body": default_body,
        }
    return {
        "subject": default_subject,
        "body": default_body,
        "uses_saved_template": False,
        "default_subject": default_subject,
        "default_body": default_body,
    }


def build_leave_request_mail(requester, leave_payload, to_admin):
    requester_name = f"{requester.get('first_name', '')} {requester.get('last_name', '')}".strip()
    requester_email = requester.get("email") or ""
    approver_name = to_admin.get("name") or "Approver"
    type_label = _type_label(leave_payload.get("type"), leave_payload.get("leave_subtype"))
    date_line = _date_line(leave_payload)
    reason = leave_payload.get("reason") or ""
    remark = leave_payload.get("remark") or ""

    subject = f"Leave / Permission Request — {requester_name} ({type_label})"

    html = f"""
<html><body style="font-family:Segoe UI,Arial,sans-serif;background:#f8fafc;padding:24px;color:#0f172a;">
<div style="max-width:640px;margin:0 auto;background:#fff;border-radius:12px;padding:28px;border:1px solid #e2e8f0;">
  <h2 style="margin:0 0 8px;color:#0f172a;">Leave &amp; Permission Request</h2>
  <p style="color:#64748b;margin:0 0 20px;">Submitted via Dce Task Manager</p>
  <p>Dear <strong>{approver_name}</strong>,</p>
  <p>
    <strong>{requester_name}</strong>
    ({requester_email or "email not on file"}) is requesting your review for the following:
  </p>
  <table style="width:100%;border-collapse:collapse;margin:16px 0;">
    <tr><td style="padding:8px 0;color:#64748b;width:140px;">Request type</td><td style="padding:8px 0;"><strong>{type_label}</strong></td></tr>
    <tr><td style="padding:8px 0;color:#64748b;">Date / time</td><td style="padding:8px 0;"><strong>{date_line}</strong></td></tr>
    <tr><td style="padding:8px 0;color:#64748b;vertical-align:top;">Reason</td><td style="padding:8px 0;">{reason}</td></tr>
    {f'<tr><td style="padding:8px 0;color:#64748b;">Remark</td><td style="padding:8px 0;">{remark}</td></tr>' if remark else ''}
  </table>
  <p style="background:#eff6ff;border-left:4px solid #2563eb;padding:12px 16px;border-radius:6px;">
    Please sign in to <strong>Dce Task Manager → Leave &amp; Permissions</strong> to approve or reject this request.
  </p>
  <p style="color:#64748b;font-size:13px;margin-top:24px;">Regards,<br>{requester_name}</p>
</div>
</body></html>
"""
    return subject, html


def build_leave_decision_mail(leave, requester, reviewer, status, review_comment=None):
    requester_name = f"{requester.get('first_name', '')} {requester.get('last_name', '')}".strip()
    reviewer_name = f"{reviewer.get('first_name', '')} {reviewer.get('last_name', '')}".strip()
    approved = status == "approved"
    type_label = _type_label(leave.type, leave.leave_subtype)
    start = leave.start_date.isoformat() if leave.start_date else ""
    end = leave.end_date.isoformat() if leave.end_date else start
    date_line = start if start == end else f"{start} to {end}"

    subject = f"Your leave request has been {'approved' if approved else 'rejected'} — {type_label}"

    status_color = "#059669" if approved else "#dc2626"
    status_word = "Approved" if approved else "Rejected"

    html = f"""
<html><body style="font-family:Segoe UI,Arial,sans-serif;background:#f8fafc;padding:24px;color:#0f172a;">
<div style="max-width:640px;margin:0 auto;background:#fff;border-radius:12px;padding:28px;border:1px solid #e2e8f0;">
  <h2 style="margin:0;color:{status_color};">Request {status_word}</h2>
  <p style="color:#64748b;margin-top:8px;">Leave &amp; Permission — Dce Task Manager</p>
  <p>Hi <strong>{requester_name}</strong>,</p>
  <p>Your <strong>{type_label}</strong> request for <strong>{date_line}</strong> has been <strong style="color:{status_color};">{status_word.lower()}</strong> by <strong>{reviewer_name}</strong>.</p>
  {f'<p style="background:#f1f5f9;padding:12px 16px;border-radius:8px;"><strong>Comment:</strong> {review_comment}</p>' if review_comment else ''}
  <p style="color:#64748b;font-size:13px;">You can view full details in the app under Leave &amp; Permissions.</p>
</div>
</body></html>
"""
    return subject, html


def send_leave_submission_email(
    requester,
    leave_payload,
    to_admin_id,
    cc_admin_ids,
    mail_subject=None,
    mail_body=None,
):
    to_admin = admin_by_id(to_admin_id)
    if not to_admin or not to_admin.email:
        return {"error": "Approver admin has no email on file"}
    to_row = _admin_recipient_row(to_admin)
    if mail_subject and mail_body:
        subject = mail_subject.strip()
        html = plain_body_to_html(mail_body)
    else:
        subject, html = build_leave_request_mail(requester, leave_payload, to_row)
    cc_emails = admin_emails_by_ids(cc_admin_ids or [])
    reply_to = requester.get("email")
    return send_html_email(to_admin.email, subject, html, cc_emails=cc_emails, reply_to=reply_to)


def send_leave_decision_email(leave, status, review_comment, reviewer_role, reviewer_role_id):
    requester = get_person_details(leave.role, leave.role_id)
    if not requester or not requester.get("email"):
        return {"error": "Requester has no email on file"}
    reviewer = get_person_details(reviewer_role, reviewer_role_id)
    if not reviewer:
        reviewer = {"first_name": "Admin", "last_name": "", "email": None}
    subject, html = build_leave_decision_mail(leave, requester, reviewer, status, review_comment)
    return send_html_email(requester["email"], subject, html)
