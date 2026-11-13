import datetime
from src import db

class LeaveRequest(db.Model):
    __tablename__ = "leave_requests"
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    role_id = db.Column(db.Integer, nullable=False)
    role = db.Column(db.String(50), nullable=False)
    type = db.Column(db.String(20), nullable=False) # leave | permission
    leave_subtype = db.Column(db.String(20), nullable=True) # full_day | half_day (only for leave type)
    reason = db.Column(db.Text, nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=True) # for permission or half-day only
    end_time = db.Column(db.Time, nullable=True) # for permission or half-day only
    attachment_path = db.Column(db.String(500), nullable=True)
    status = db.Column(db.String(20), default='pending') # pending | approved | rejected | cancelled
    reviewed_by_role_id = db.Column(db.Integer, nullable=True)
    reviewed_by_role = db.Column(db.String(50), nullable=True)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    review_comment = db.Column(db.Text, nullable=True)
    remark = db.Column(db.Text, nullable=True)
    notify_to_admin_id = db.Column(db.Integer, nullable=True)
    notify_cc_admin_ids = db.Column(db.Text, nullable=True)  # JSON array of admin ids
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    def __repr__(self):
        return f"<LeaveRequest {self.id} for {self.role} {self.role_id} - {self.status}>"


class LeaveRequestAudit(db.Model):
    __tablename__ = "leave_request_audits"
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    leave_request_id = db.Column(db.Integer, db.ForeignKey('leave_requests.id'), nullable=False)
    action = db.Column(db.String(50), nullable=False) # created | updated | cancelled | approved | rejected
    old_status = db.Column(db.String(20), nullable=True)
    new_status = db.Column(db.String(20), nullable=True)
    performed_by_role_id = db.Column(db.Integer, nullable=False)
    performed_by_role = db.Column(db.String(50), nullable=False)
    performed_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    comment = db.Column(db.Text, nullable=True)
    
    def __repr__(self):
        return f"<LeaveRequestAudit {self.id} for leave {self.leave_request_id} - {self.action}>"
