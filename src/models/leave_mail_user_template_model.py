import datetime
from src import db


class LeaveMailUserTemplate(db.Model):
    """Per-user saved subject/body text for leave request emails (no admin UI)."""

    __tablename__ = "leave_mail_user_templates"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    role_id = db.Column(db.Integer, nullable=False)
    role = db.Column(db.String(50), nullable=False)
    subject = db.Column(db.String(500), nullable=False, default="")
    body = db.Column(db.Text, nullable=False, default="")
    updated_at = db.Column(
        db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow
    )

    __table_args__ = (
        db.UniqueConstraint("role_id", "role", name="uq_leave_mail_template_user"),
    )
