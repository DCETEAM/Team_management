import datetime

from src import db


class ProjectCredential(db.Model):
    __tablename__ = "project_credentials"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False, index=True)
    label = db.Column(db.String(120), nullable=False)
    username = db.Column(db.String(255), nullable=False)
    password_encrypted = db.Column(db.Text, nullable=False)
    notes = db.Column(db.Text, nullable=True)
    created_by_role_id = db.Column(db.Integer, nullable=True)
    created_by_role = db.Column(db.String(32), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow
    )

    project = db.relationship("Project", backref=db.backref("credentials", lazy="dynamic"))

    __table_args__ = (
        db.UniqueConstraint("project_id", "label", name="uq_project_credential_label"),
    )
