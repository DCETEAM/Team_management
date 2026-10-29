import datetime
from src import db


class TaskStatusHistory(db.Model):
    __tablename__ = "task_status_history"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    task_id = db.Column(db.Integer, db.ForeignKey("tasks.id"), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False)
    sprint_id = db.Column(db.Integer, db.ForeignKey("sprints.id"), nullable=True)
    task_title = db.Column(db.String(500), nullable=True)

    from_status_id = db.Column(db.Integer, nullable=True)
    to_status_id = db.Column(db.Integer, nullable=False)
    from_status_name = db.Column(db.String(120), nullable=True)
    to_status_name = db.Column(db.String(120), nullable=True)

    changed_by_role_id = db.Column(db.Integer, nullable=True)
    changed_by_role = db.Column(db.String(50), nullable=True)
    changed_by_first_name = db.Column(db.String(120), nullable=True)
    changed_by_last_name = db.Column(db.String(120), nullable=True)
    changed_by_email = db.Column(db.String(255), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    task = db.relationship("Task", backref="status_history_entries")

    def __repr__(self):
        return f"<TaskStatusHistory task={self.task_id} {self.from_status_name}->{self.to_status_name}>"
