import datetime
from src import db

class Worker(db.Model):
    __tablename__ = "workers"
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(150), nullable=True)
    avatar_url = db.Column(db.Text(length=16777215), nullable=True) # MEDIUMTEXT for MySQL
    is_tl = db.Column(db.Boolean, default=False)
    is_worker = db.Column(db.Boolean, default=True)
    job_title = db.Column(db.String(255), nullable=True)
    department = db.Column(db.String(255), nullable=True)
    experience_years = db.Column(db.Float, nullable=True)
    working_hours = db.Column(db.Integer, nullable=True)
    work_mode = db.Column(db.Enum('WFH', 'OFFICE', 'HYBRID', name='worker_work_mode_enum'), nullable=True)
    office_location = db.Column(db.String(255), nullable=True)
    github_url = db.Column(db.String(255), nullable=True)
    linkedin_url = db.Column(db.String(255), nullable=True)
    portfolio_url = db.Column(db.String(255), nullable=True)
    address_line1 = db.Column(db.String(255), nullable=True)
    address_line2 = db.Column(db.String(255), nullable=True)
    city = db.Column(db.String(100), nullable=True)
    state = db.Column(db.String(100), nullable=True)
    country = db.Column(db.String(100), nullable=True)
    pincode = db.Column(db.String(20), nullable=True)
    joining_date = db.Column(db.Date, nullable=True)
    employment_type = db.Column(db.Enum('FULL_TIME', 'INTERN', 'CONTRACT', name='employment_type_enum'), nullable=True)
    status = db.Column(db.Enum('ACTIVE', 'INACTIVE', 'RESIGNED', name='worker_status_enum'), default='ACTIVE')
    remark = db.Column(db.Text, nullable=True)
    profile_onboarding_completed = db.Column(db.Boolean, default=False, nullable=False)
    profile_onboarding_skipped = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    def __repr__(self):
        return f"<Worker {self.first_name} {self.last_name}>"
