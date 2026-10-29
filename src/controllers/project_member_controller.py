from flask import jsonify
from src import db
from src.models.project_allocation_model import ProjectAllocation
from src.models.admin_model import Admin
from src.models.worker_model import Worker

def get_project_members(project_id, decoded_payload=None):
    try:
        allocation = ProjectAllocation.query.filter_by(project_id=project_id).first()
        
        allocated_member_ids = []
        if allocation and allocation.members:
            for m in allocation.members:
                # Handle both formats: old {user_id} and new {role_id}
                user_id = m.get("user_id")
                role_id = m.get("role_id")
                if user_id:
                    allocated_member_ids.append(user_id)
                elif role_id:
                    allocated_member_ids.append(role_id)
        
        all_admins = Admin.query.all()
        all_workers = Worker.query.all()
        
        members = []
        
        for admin in all_admins:
            is_allocated = admin.id in allocated_member_ids
            member_data = {
                "id": admin.id,
                "type": "admin",
                "first_name": admin.first_name,
                "last_name": admin.last_name,
                "email": admin.email,
                "avatar_url": admin.avatar_url,
                "is_superadmin": admin.is_superadmin,
                "is_admin": admin.is_admin,
                "is_scrum": admin.is_scrum,
                "is_allocated": is_allocated
            }
            members.append(member_data)
        
        for worker in all_workers:
            is_allocated = worker.id in allocated_member_ids
            member_data = {
                "id": worker.id,
                "type": "worker",
                "first_name": worker.first_name,
                "last_name": worker.last_name,
                "email": worker.email,
                "avatar_url": worker.avatar_url,
                "is_tl": worker.is_tl,
                "is_worker": worker.is_worker,
                "job_title": worker.job_title,
                "is_allocated": is_allocated
            }
            members.append(member_data)
        
        return jsonify({"members": members, "status": 1}), 200
    except Exception as e:
        import traceback
        print(f"Error in get_project_members: {str(e)}")
        print(traceback.format_exc())
        return jsonify({"success": 0, "error": str(e)}), 500
