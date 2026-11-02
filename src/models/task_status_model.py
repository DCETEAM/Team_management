import datetime
from src import db

class TaskStatus(db.Model):
    __tablename__ = "task_statuses"
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(50), nullable=False, unique=True) # to_do | in_progress | in_review | done | cancelled
    color = db.Column(db.String(10), nullable=True) # hex e.g. #FF5630
    sort_order = db.Column(db.Integer, default=0)
    remark = db.Column(db.Text, nullable=True)
    is_confidential = db.Column(db.Boolean, default=False)
    is_backlog = db.Column(db.Boolean, default=False)
    is_todo = db.Column(db.Boolean, default=False)
    is_in_progress = db.Column(db.Boolean, default=False)
    is_pending = db.Column(db.Boolean, default=False)
    is_hold = db.Column(db.Boolean, default=False)
    is_review = db.Column(db.Boolean, default=False)
    is_completed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    def __repr__(self):
        return f"<TaskStatus {self.name}>"
