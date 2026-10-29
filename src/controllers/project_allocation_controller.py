from flask import jsonify, request
import datetime
from src import db
from src.models.project_allocation_model import ProjectAllocation
from src.models.worker_model import Worker
from src.models.admin_model import Admin
from src.utils.role_utils import get_person_details
from src.utils.date_utils import safe_isoformat
from src.utils.request_client_time import stamp_model_times, touch_updated_at

def sanitize_member(member):
    """Only keep necessary fields for storage: role_id, parent_id, client_contact, and basic identification."""
    sanitized = {}
    if "role_id" in member:
        sanitized["role_id"] = member["role_id"]
    if "parent_id" in member:
        sanitized["parent_id"] = member["parent_id"]
    if "client_contact" in member:
        sanitized["client_contact"] = bool(member["client_contact"])
    # Also keep basic identification for reference
    if "role" in member:
        sanitized["role"] = member["role"]
    if "user_id" in member:
        sanitized["user_id"] = member["user_id"]
    return sanitized

def create_allocation(decoded_payload=None):
    try:
        data = request.get_json()
        print(data)
        
        project_id = data.get("project_id")
        members = data.get("members", []) # Default to empty list
        start_date_str = data.get("start_date")
        end_date_str = data.get("end_date")
        remark = data.get("remark")
        
        allocated_by_role_id = data.get("role_id")
        allocated_by_role = data.get("role")
        
        if not all([project_id, start_date_str, allocated_by_role_id, allocated_by_role]):
            return jsonify({"msg": "Project ID, start date, role_id, and role are required", "status": 0}), 400

        if members and not isinstance(members, list):
            return jsonify({"msg": "Members must be a JSON array", "status": 0}), 400

        # Check for existing allocation for this project
        existing = ProjectAllocation.query.filter_by(project_id=project_id).first()
        if existing:
            return jsonify({"msg": "Project allocation already exists for this project", "status": 0}), 409

        try:
            start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None
        except ValueError:
            return jsonify({"msg": "Invalid date format. Use YYYY-MM-DD", "status": 0}), 400

        # Sanitize members
        sanitized_members = [sanitize_member(m) for m in members]

        new_allocation = ProjectAllocation(
            project_id=project_id,
            members=sanitized_members,
            start_date=start_date,
            end_date=end_date,
            remark=remark.strip() if remark else None,
            allocated_by_role_id=allocated_by_role_id,
            allocated_by_role=allocated_by_role
        )
        err = stamp_model_times(new_allocation, request, creating=True)
        if err:
            return err
        db.session.add(new_allocation)
        db.session.commit()
        
        return jsonify({"msg": "Project allocation created successfully", "status": 1, "id": new_allocation.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": 0, "error": str(e)}), 500

def normalize_role_name(role_name):
    """Convert role name to lowercase snake_case for consistency."""
    if not role_name:
        return None
    return role_name.strip().lower().replace(" ", "_")

def get_all_allocations(decoded_payload=None):
    try:
        allocations = ProjectAllocation.query.all()
        result = []
        for alloc in allocations:
            allocated_by_person = get_person_details(alloc.allocated_by_role, alloc.allocated_by_role_id)
            # Enrich members
            enriched_members = []
            if alloc.members:
                for member in alloc.members:
                    member_role = member.get("role")
                    member_user_id = member.get("user_id")
                    if member_role and member_user_id:
                        normalized_role = normalize_role_name(member_role)
                        member_details = get_person_details(normalized_role, member_user_id)
                        if member_details:
                            # Merge member details with original member to preserve client_contact, parent_id, etc.
                            merged_member = {**member_details, **member}
                            enriched_members.append(merged_member)
                        else:
                            enriched_members.append(member)
                    else:
                        enriched_members.append(member)
            result.append({
                "id": alloc.id,
                "project_id": alloc.project_id,
                "project_name": alloc.project.name if alloc.project else None,
                "project_logo": alloc.project.project_logo if alloc.project else None,
                "members": enriched_members,
                "start_date": safe_isoformat(alloc.start_date),
                "end_date": safe_isoformat(alloc.end_date),
                "remark": alloc.remark,
                "allocated_by_role_id": alloc.allocated_by_role_id,
                "allocated_by_role": alloc.allocated_by_role,
                "allocated_by_person": allocated_by_person,
                "created_at": alloc.created_at
            })
        return jsonify({"allocations": result, "status": 1}), 200
    except Exception as e:
        print(f"Error in get_all_allocations: {str(e)}")
        return jsonify({"success": 0, "error": str(e)}), 500

def get_allocation_by_project_id(project_id, decoded_payload=None):
    try:
        alloc = ProjectAllocation.query.filter_by(project_id=project_id).first()
        if not alloc:
            # Return empty structure if not found
            return jsonify({
                "allocation": {
                    "project_id": project_id,
                    "members": [],
                }, 
                "status": 1
            }), 200
        
        allocated_by_person = get_person_details(alloc.allocated_by_role, alloc.allocated_by_role_id)
        # Enrich members
        enriched_members = []
        if alloc.members:
            for member in alloc.members:
                member_role = member.get("role")
                member_user_id = member.get("user_id")
                if member_role and member_user_id:
                    normalized_role = normalize_role_name(member_role)
                    member_details = get_person_details(normalized_role, member_user_id)
                    if member_details:
                        # Merge member details with original member to preserve client_contact, parent_id, etc.
                        merged_member = {**member_details, **member}
                        enriched_members.append(merged_member)
                    else:
                        enriched_members.append(member)
                else:
                    enriched_members.append(member)

        result = {
            "id": alloc.id,
            "project_id": alloc.project_id,
            "project_name": alloc.project.name if alloc.project else None,
            "project_logo": alloc.project.project_logo if alloc.project else None,
            "members": enriched_members,
            "start_date": safe_isoformat(alloc.start_date),
            "end_date": safe_isoformat(alloc.end_date),
            "remark": alloc.remark,
            "allocated_by_role_id": alloc.allocated_by_role_id,
            "allocated_by_role": alloc.allocated_by_role,
            "allocated_by_person": allocated_by_person,
            "created_at": alloc.created_at
        }
        return jsonify({"allocation": result, "status": 1}), 200
    except Exception as e:
        print(f"Error in get_allocation_by_project_id: {str(e)}")
        return jsonify({"success": 0, "error": str(e)}), 500

def get_allocation_by_id(allocation_id, decoded_payload=None):
    try:
        alloc = ProjectAllocation.query.get(allocation_id)
        if not alloc:
            return jsonify({"message": "Allocation not found", "status": 0}), 404
        
        allocated_by_person = get_person_details(alloc.allocated_by_role, alloc.allocated_by_role_id)
        # Enrich members
        enriched_members = []
        if alloc.members:
            for member in alloc.members:
                member_role = member.get("role")
                member_user_id = member.get("user_id")
                if member_role and member_user_id:
                    normalized_role = normalize_role_name(member_role)
                    member_details = get_person_details(normalized_role, member_user_id)
                    if member_details:
                        # Merge member details with original member to preserve client_contact, parent_id, etc.
                        merged_member = {**member_details, **member}
                        enriched_members.append(merged_member)
                    else:
                        enriched_members.append(member)
                else:
                    enriched_members.append(member)
        
        result = {
            "id": alloc.id,
            "project_id": alloc.project_id,
            "project_name": alloc.project.name if alloc.project else None,
            "project_logo": alloc.project.project_logo if alloc.project else None,
            "members": enriched_members,
            "start_date": safe_isoformat(alloc.start_date),
            "end_date": safe_isoformat(alloc.end_date),
            "remark": alloc.remark,
            "allocated_by_role_id": alloc.allocated_by_role_id,
            "allocated_by_role": alloc.allocated_by_role,
            "allocated_by_person": allocated_by_person,
            "created_at": alloc.created_at
        }
        return jsonify({"allocation": result, "status": 1}), 200
    except Exception as e:
        print(f"Error in get_allocation_by_id: {str(e)}")
        return jsonify({"success": 0, "error": str(e)}), 500

def update_allocation(allocation_id, decoded_payload=None):
    try:
        alloc = ProjectAllocation.query.get(allocation_id)
        if not alloc:
            return jsonify({"message": "Allocation not found", "status": 0}), 404

        data = request.get_json()
        
        if "project_id" in data:
            alloc.project_id = data["project_id"]
        if "members" in data:
            if not isinstance(data["members"], list):
                return jsonify({"msg": "Members must be a JSON array", "status": 0}), 400
            # Sanitize members
            sanitized_members = [sanitize_member(m) for m in data["members"]]
            alloc.members = sanitized_members
        if "start_date" in data:
            alloc.start_date = datetime.datetime.strptime(data["start_date"], '%Y-%m-%d').date()
        if "end_date" in data:
            alloc.end_date = datetime.datetime.strptime(data["end_date"], '%Y-%m-%d').date() if data["end_date"] else None
        if "remark" in data:
            alloc.remark = data["remark"].strip() if data["remark"] else None

        err = touch_updated_at(alloc, request)
        if err:
            return err
            
        db.session.commit()
        return jsonify({"message": "Allocation updated successfully", "status": 1}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": 0, "error": str(e)}), 500

def update_allocation_members(allocation_id, decoded_payload=None):
    try:
        alloc = ProjectAllocation.query.get(allocation_id)
        if not alloc:
            return jsonify({"message": "Allocation not found", "status": 0}), 404

        data = request.get_json()
        members = data.get("members")
        
        if members is not None:
            if not isinstance(members, list):
                return jsonify({"msg": "Members must be a JSON array", "status": 0}), 400
            # Sanitize members
            sanitized_members = [sanitize_member(m) for m in members]
            alloc.members = sanitized_members
            err = touch_updated_at(alloc, request)
            if err:
                return err
            db.session.commit()
            return jsonify({"message": "Members updated successfully", "status": 1}), 200
        
        return jsonify({"msg": "No members data provided", "status": 0}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": 0, "error": str(e)}), 500

def get_available_users_by_project(project_id, decoded_payload=None):
    try:
        alloc = ProjectAllocation.query.filter_by(project_id=project_id).first()
        available_users = []
        worker_user_ids = set()
        
        # First add allocated workers and admins from allocation
        if alloc and alloc.members:
            for member in alloc.members:
                user_id = member.get("user_id")
                role = member.get("role")
                if not user_id:
                    continue
                
                user = None
                if role and "admin" in role.lower():
                    user = Admin.query.get(user_id)
                    if user:
                        available_users.append({
                            "type": "admin",
                            "user_id": user.id,
                            "first_name": user.first_name,
                            "last_name": user.last_name,
                            "email": user.email,
                            "avatar_url": user.avatar_url,
                            "role": role
                        })
                else:
                    user = Worker.query.get(user_id)
                    if user:
                        worker_user_ids.add(user_id)
                        available_users.append({
                            "type": "worker",
                            "user_id": user.id,
                            "first_name": user.first_name,
                            "last_name": user.last_name,
                            "email": user.email,
                            "avatar_url": user.avatar_url,
                            "role": role
                        })
        
        # Now add all remaining admins from admin table that are not already in the list
        all_admins = Admin.query.all()
        for admin in all_admins:
            # Check if admin is not already in the list
            if not any(u["type"] == "admin" and u["user_id"] == admin.id for u in available_users):
                available_users.append({
                    "type": "admin",
                    "user_id": admin.id,
                    "first_name": admin.first_name,
                    "last_name": admin.last_name,
                    "email": admin.email,
                    "avatar_url": admin.avatar_url,
                    "role": "Admin"
                })
        
        # Sort the list: workers first, then admins
        available_users.sort(key=lambda x: 0 if x["type"] == "worker" else 1)
        
        return jsonify({"available_users": available_users, "status": 1}), 200
    except Exception as e:
        print(f"Error getting available users: {str(e)}")
        return jsonify({"success": 0, "error": str(e)}), 500

def delete_allocation(allocation_id, decoded_payload=None):
    try:
        alloc = ProjectAllocation.query.get(allocation_id)
        if not alloc:
            return jsonify({"msg": "Allocation not found", "status": 0}), 404
            
        db.session.delete(alloc)
        db.session.commit()
        return jsonify({"msg": "Allocation deleted successfully", "status": 1}), 200
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting allocation: {str(e)}")
        return jsonify({"success": 0, "msg": "Failed to delete allocation. Please try again later.", "status": 0}), 500
