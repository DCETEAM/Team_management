import datetime
import secrets
import hashlib
from src import db


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class MonitorDevice(db.Model):
    __tablename__ = "monitor_devices"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    device_uuid = db.Column(db.String(64), unique=True, nullable=False, index=True)
    device_name = db.Column(db.String(255), nullable=True)
    operating_system = db.Column(db.String(100), nullable=True)
    agent_version = db.Column(db.String(50), nullable=True)
    token_hash = db.Column(db.String(64), nullable=False)
    status = db.Column(db.String(20), default="active", nullable=False)  # active | revoked
    last_seen_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    user = db.relationship("User", backref=db.backref("monitor_devices", lazy="dynamic"))

    def verify_token(self, token: str) -> bool:
        return self.token_hash == _hash_token(token)

    @staticmethod
    def generate_token():
        return secrets.token_urlsafe(32)


class MonitorPairingCode(db.Model):
    __tablename__ = "monitor_pairing_codes"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    code = db.Column(db.String(12), unique=True, nullable=False, index=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    used_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)


class WorkSession(db.Model):
    __tablename__ = "work_sessions"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    device_id = db.Column(db.Integer, db.ForeignKey("monitor_devices.id"), nullable=False, index=True)
    task_id = db.Column(db.Integer, db.ForeignKey("tasks.id"), nullable=True, index=True)
    started_at = db.Column(db.DateTime, nullable=False)
    ended_at = db.Column(db.DateTime, nullable=True)
    last_heartbeat_at = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(30), default="active", nullable=False)
    active_seconds = db.Column(db.Integer, default=0, nullable=False)
    idle_seconds = db.Column(db.Integer, default=0, nullable=False)
    break_seconds = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    device = db.relationship("MonitorDevice", backref=db.backref("sessions", lazy="dynamic"))
    user = db.relationship("User", backref=db.backref("work_sessions", lazy="dynamic"))
    task = db.relationship("Task", backref=db.backref("work_sessions", lazy="dynamic"))


class ActivityEvent(db.Model):
    __tablename__ = "activity_events"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    event_uuid = db.Column(db.String(64), unique=True, nullable=False, index=True)
    session_id = db.Column(db.Integer, db.ForeignKey("work_sessions.id"), nullable=False, index=True)
    event_type = db.Column(db.String(50), nullable=False)
    occurred_at = db.Column(db.DateTime, nullable=False)
    received_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, nullable=False)
    metadata_json = db.Column("metadata", db.JSON, nullable=True)

    session = db.relationship("WorkSession", backref=db.backref("events", lazy="dynamic"))


class AppUsageSegment(db.Model):
    __tablename__ = "app_usage_segments"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    session_id = db.Column(db.Integer, db.ForeignKey("work_sessions.id"), nullable=False, index=True)
    app_category = db.Column(db.String(100), nullable=True)
    app_name = db.Column(db.String(255), nullable=True)
    started_at = db.Column(db.DateTime, nullable=False)
    ended_at = db.Column(db.DateTime, nullable=True)
    duration_seconds = db.Column(db.Integer, default=0, nullable=False)

    session = db.relationship("WorkSession", backref=db.backref("app_segments", lazy="dynamic"))


class DailyWorkSummary(db.Model):
    __tablename__ = "daily_work_summaries"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    work_date = db.Column(db.Date, nullable=False, index=True)
    tracked_seconds = db.Column(db.Integer, default=0, nullable=False)
    active_seconds = db.Column(db.Integer, default=0, nullable=False)
    idle_seconds = db.Column(db.Integer, default=0, nullable=False)
    break_seconds = db.Column(db.Integer, default=0, nullable=False)
    tasks_completed = db.Column(db.Integer, default=0, nullable=False)
    generated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("user_id", "work_date", name="uq_daily_work_user_date"),
    )
