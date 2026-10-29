import datetime
from src import db

class User(db.Model):
    __tablename__ = "users"
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    role_id = db.Column(db.Integer, nullable=True) # admins.id OR workers.id
    role = db.Column(db.String(50), nullable=False) # superadmin | admin | scrum | team_leader | worker
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Auth specific fields
    refresh_token = db.Column(db.Text)
    refresh_token_created_at = db.Column(
        db.DateTime, default=datetime.datetime.utcnow
    )
    profile_onboarding_completed = db.Column(db.Boolean, default=False, nullable=False)
    profile_onboarding_skipped = db.Column(db.Boolean, default=False, nullable=False)

    def __repr__(self):
        return f"<User {self.email}>"
