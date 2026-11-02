import datetime
from src import db

class Task(db.Model):
    __tablename__ = "tasks"
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    sprint_id = db.Column(db.Integer, db.ForeignKey('sprints.id'), nullable=True)
    allocation_id = db.Column(db.Integer, db.ForeignKey('project_allocations.id'), nullable=True)
    status_id = db.Column(db.Integer, db.ForeignKey('task_statuses.id'), nullable=False)
    title = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text, nullable=True)
    goal = db.Column(db.Text, nullable=True)
    priority = db.Column(db.String(20), default='medium') # low | medium | high | critical
    start_date = db.Column(db.Date, nullable=True)
    due_date = db.Column(db.Date, nullable=True)
    members = db.Column(db.JSON, nullable=True) # JSON array of [{role_id, role}]
    worker_ids = db.Column(db.JSON, nullable=True) # Backward compatibility: JSON array of worker/admin IDs
    assigned_by_role_id = db.Column(db.Integer, nullable=False) # who assigned (role_id)
    assigned_by_role = db.Column(db.String(50), nullable=False) # who assigned (role)
    assigned_by = db.Column(db.Integer, nullable=True) # Backward compatibility: user_id
    estimated_hours = db.Column(db.Numeric(6, 2), nullable=True)
    actual_hours = db.Column(db.Numeric(6, 2), nullable=True)
    remark = db.Column(db.Text, nullable=True)
    review_approved_by_role_id = db.Column(db.Integer, nullable=True)
    review_approved_by_role = db.Column(db.String(50), nullable=True)
    review_approved_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Relationships
    project = db.relationship('Project', backref='tasks')
    sprint = db.relationship('Sprint', backref='tasks')
    allocation = db.relationship('ProjectAllocation', backref='tasks')
    status = db.relationship('TaskStatus', backref='tasks')
    
    def __repr__(self):
        return f"<Task {self.title}>"
