from flask import jsonify, request
from src import db
from src.models.project_group_model import ProjectGroup
from src.models.project_model import Project
from src.utils.date_utils import safe_isoformat
from src.utils.request_client_time import stamp_model_times, touch_updated_at, require_client_now

def create_project_group(decoded_payload=None):
    try:
        data = request.get_json()
        name = data.get("name")
        description = data.get("description")
        
        # Trim name and validate
        name = name.strip() if name else None
        if not name:
            return jsonify({"msg": "Group name is required", "status": 0}), 400
            
        # Check if group name already exists
        existing_group = ProjectGroup.query.filter_by(name=name).first()
        if existing_group:
            return jsonify({"msg": "Project group name already exists", "status": 0}), 409

        new_group = ProjectGroup(
            name=name,
            description=description.strip() if description else None
        )
        err = stamp_model_times(new_group, request, creating=True)
        if err:
            return err
        db.session.add(new_group)
        db.session.commit()
        
        return jsonify({"msg": "Project group created successfully", "status": 1, "id": new_group.id}), 201
    except Exception as e:
        db.session.rollback()
        if "Duplicate entry" in str(e):
            if "name" in str(e):
                return jsonify({"msg": "Project group name already exists", "status": 0}), 409
        return jsonify({"success": 0, "error": str(e)}), 500

def get_all_project_groups(decoded_payload=None):
    try:
        groups = ProjectGroup.query.all()
        result = []
        for group in groups:
            result.append({
                "id": group.id,
                "name": group.name,
                "description": group.description,
                "project_count": len(group.projects),
                "created_at": safe_isoformat(group.created_at)
            })
        return jsonify({"groups": result, "status": 1}), 200
    except Exception as e:
        return jsonify({"success": 0, "error": str(e)}), 500

def get_project_group_by_id(group_id, decoded_payload=None):
    try:
        group = ProjectGroup.query.get(group_id)
        if not group:
            return jsonify({"msg": "Project group not found", "status": 0}), 404
            
        projects = []
        for project in group.projects:
            projects.append({
                "id": project.id,
                "name": project.name,
                "status": project.status
            })
            
        result = {
            "id": group.id,
            "name": group.name,
            "description": group.description,
            "projects": projects,
            "created_at": safe_isoformat(group.created_at)
        }
        return jsonify({"group": result, "status": 1}), 200
    except Exception as e:
        return jsonify({"success": 0, "error": str(e)}), 500

def update_project_group(group_id, decoded_payload=None):
    try:
        group = ProjectGroup.query.get(group_id)
        if not group:
            return jsonify({"msg": "Project group not found", "status": 0}), 404

        data = request.get_json()
        if "name" in data:
            name = data["name"].strip() if data["name"] else None
            if not name:
                return jsonify({"msg": "Group name is required", "status": 0}), 400
            # Check if name is taken by another group
            existing = ProjectGroup.query.filter_by(name=name).first()
            if existing and existing.id != group_id:
                return jsonify({"msg": "Project group name already exists", "status": 0}), 409
            group.name = name
            
        if "description" in data:
            group.description = data["description"].strip() if data["description"] else None

        err = touch_updated_at(group, request)
        if err:
            return err
            
        db.session.commit()
        return jsonify({"msg": "Project group updated successfully", "status": 1}), 200
    except Exception as e:
        db.session.rollback()
        if "Duplicate entry" in str(e):
            if "name" in str(e):
                return jsonify({"msg": "Project group name already exists", "status": 0}), 409
        return jsonify({"success": 0, "error": str(e)}), 500

def delete_project_group(group_id, decoded_payload=None):
    try:
        group = ProjectGroup.query.get(group_id)
        if not group:
            return jsonify({"msg": "Project group not found", "status": 0}), 404
            
        # Dissociate projects before deleting the group
        for project in group.projects:
            project.group_id = None
            
        db.session.delete(group)
        db.session.commit()
        return jsonify({"msg": "Project group deleted successfully", "status": 1}), 200
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting project group: {str(e)}")
        return jsonify({"success": 0, "msg": "Failed to delete project group. Please try again later.", "status": 0}), 500

def add_projects_to_group(group_id, decoded_payload=None):
    try:
        group = ProjectGroup.query.get(group_id)
        if not group:
            return jsonify({"msg": "Project group not found", "status": 0}), 404
            
        data = request.get_json()
        project_ids = data.get("project_ids", [])
        
        if not isinstance(project_ids, list):
            return jsonify({"msg": "project_ids must be a list", "status": 0}), 400

        now, err = require_client_now(request)
        if err:
            return err
            
        for pid in project_ids:
            project = Project.query.get(pid)
            if project:
                project.group_id = group_id
                project.updated_at = now
        group.updated_at = now
                
        db.session.commit()
        return jsonify({"msg": "Projects added to group successfully", "status": 1}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": 0, "error": str(e)}), 500
