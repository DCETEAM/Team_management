from flask import jsonify, request
import datetime
from src import db
from src.models.project_model import Project
from src.models.project_allocation_model import ProjectAllocation
from src.models.sprint_model import Sprint
from src.utils.date_utils import parse_date, safe_isoformat
from src.utils.image_utils import save_image
from src.utils.role_utils import get_person_details
from src.utils.request_client_time import stamp_model_times, touch_updated_at


def create_project(decoded_payload=None):
    try:
        data = request.get_json()
        print(data)
        
        client_id = data.get("client_id")
        name = data.get("name")
        description = data.get("description")
        start_date_str = data.get("start_date")
        end_date_str = data.get("end_date")
        status = data.get("status", "active")
        group_id = data.get("group_id")

        remark = data.get("remark")
        project_logo = data.get("project_logo")
        by_tl_managed = data.get("by_tl_managed", False)
        team_managed = data.get("team_managed", False)
        company_managed = data.get("company_managed", False)
        
        # Save project logo if provided as base64
        saved_logo_url = save_image(project_logo, folder="project_logos")
        final_logo_url = saved_logo_url if saved_logo_url else project_logo
        
        created_by_role_id = decoded_payload.get("role_id") if decoded_payload else None
        created_by_role = decoded_payload.get("role") if decoded_payload else None
        
        # Trim name
        name = name.strip() if name else None
        if not all([name, start_date_str, client_id, group_id]):
            return jsonify({"msg": "Project name, start date, client and project group are required", "status": 0}), 400

        start_date = parse_date(start_date_str)
        end_date = parse_date(end_date_str) if end_date_str else None

        if not start_date:
            return jsonify({"msg": "Invalid start date format", "status": 0}), 400

        new_project = Project(
            client_id=client_id,
            name=name,
            group_id=group_id,
            description=description.strip() if description else None,
            start_date=start_date,
            end_date=end_date,
            status=status,
            project_logo=final_logo_url,
            remark=remark.strip() if remark else None,
            by_tl_managed=by_tl_managed,
            team_managed=team_managed,
            company_managed=company_managed,
            created_by_role_id=created_by_role_id,
            created_by_role=created_by_role
        )
        err = stamp_model_times(new_project, request, creating=True)
        if err:
            return err
        db.session.add(new_project)
        db.session.commit()
        
        # Automatically create a project allocation entry
        new_allocation = ProjectAllocation(
            project_id=new_project.id,
            members=[], # Default to empty list as requested
            start_date=start_date,
            end_date=end_date,
            remark=remark.strip() if remark else None,
            allocated_by_role_id=created_by_role_id,
            allocated_by_role=created_by_role
        )
        err = stamp_model_times(new_allocation, request, creating=True)
        if err:
            db.session.rollback()
            return err
        db.session.add(new_allocation)
        db.session.commit()
        
        return jsonify({"msg": "Project created successfully and allocation initialized", "status": 1, "project_id": new_project.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": 0, "error": str(e)}), 500

def get_all_projects(decoded_payload=None):
    try:
        role = request.args.get("role")
        role_id = request.args.get("role_id")
        if role_id:
            role_id = int(role_id)
        
        projects = Project.query.all()
        
        # Filter projects for team_leader or worker based on allocation
        if role in ["team_leader", "worker"] and role_id:
            filtered_project_ids = []
            allocations = ProjectAllocation.query.all()
            for alloc in allocations:
                members = alloc.members or []
                for member in members:
                    if member.get("user_id") == role_id:
                        filtered_project_ids.append(alloc.project_id)
                        break
            
            # Filter projects to only those in filtered_project_ids
            projects = [p for p in projects if p.id in filtered_project_ids]
        
        result = []
        for project in projects:
            created_by_person = get_person_details(project.created_by_role, project.created_by_role_id)
            # Get project sprints
            project_sprints = Sprint.query.filter_by(project_id=project.id).order_by(Sprint.created_at.desc()).all()
            sprints = []
            for sprint in project_sprints:
                # Get task count for the sprint
                from src.models.task_model import Task
                task_count = Task.query.filter_by(sprint_id=sprint.id).count()
                
                sprints.append({
                    "id": sprint.id,
                    "project_id": sprint.project_id,
                    "sprint_name": sprint.sprint_name,
                    "sprint_goal": sprint.sprint_goal,
                    "description": sprint.description,
                    "start_date": safe_isoformat(sprint.start_date),
                    "end_date": safe_isoformat(sprint.end_date),
                    "status": sprint.status,
                    "is_active": sprint.is_active,
                    "sprint_status": sprint.sprint_status,
                    "task_count": task_count,
                    "created_by": sprint.created_by,
                    "updated_by": sprint.updated_by,
                    "created_at": safe_isoformat(sprint.created_at),
                    "updated_at": safe_isoformat(sprint.updated_at)
                })
            result.append({
                "id": project.id,
                "client_id": project.client_id,
                "client_name": project.client.name if project.client else None,
                "name": project.name,
                "group_id": project.group_id,
                "group_name": project.group.name if project.group else None,
                "description": project.description,
                "start_date": safe_isoformat(project.start_date),
                "end_date": safe_isoformat(project.end_date),
                "status": project.status,
                "project_logo": project.project_logo,
                "remark": project.remark,
                "by_tl_managed": project.by_tl_managed,
                "team_managed": project.team_managed,
                "company_managed": project.company_managed,
                "created_by_role_id": project.created_by_role_id,
                "created_by_role": project.created_by_role,
                "created_by_person": created_by_person,
                "created_at": safe_isoformat(project.created_at),
                "sprints": sprints
            })
        return jsonify({"projects": result, "status": 1}), 200
    except Exception as e:
        return jsonify({"success": 0, "error": str(e)}), 500

def get_project_by_id(project_id, decoded_payload=None):
    try:
        project = Project.query.get(project_id)
        if not project:
            return jsonify({"message": "Project not found", "status": 0}), 404
        
        created_by_person = get_person_details(project.created_by_role, project.created_by_role_id)
        # Get project sprints
        project_sprints = Sprint.query.filter_by(project_id=project.id).order_by(Sprint.created_at.desc()).all()
        sprints = []
        for sprint in project_sprints:
            # Get task count for the sprint
            from src.models.task_model import Task
            task_count = Task.query.filter_by(sprint_id=sprint.id).count()
            
            sprints.append({
                "id": sprint.id,
                "project_id": sprint.project_id,
                "sprint_name": sprint.sprint_name,
                "sprint_goal": sprint.sprint_goal,
                "description": sprint.description,
                "start_date": safe_isoformat(sprint.start_date),
                "end_date": safe_isoformat(sprint.end_date),
                "status": sprint.status,
                "is_active": sprint.is_active,
                "sprint_status": sprint.sprint_status,
                "task_count": task_count,
                "created_by": sprint.created_by,
                "updated_by": sprint.updated_by,
                "created_at": safe_isoformat(sprint.created_at),
                "updated_at": safe_isoformat(sprint.updated_at)
            })
        result = {
            "id": project.id,
            "client_id": project.client_id,
            "client_name": project.client.name if project.client else None,
            "group_id": project.group_id,
            "group_name": project.group.name if project.group else None,
            "name": project.name,
            "description": project.description,
            "start_date": safe_isoformat(project.start_date),
            "end_date": safe_isoformat(project.end_date),
            "status": project.status,
            "project_logo": project.project_logo,
            "remark": project.remark,
            "by_tl_managed": project.by_tl_managed,
            "team_managed": project.team_managed,
            "company_managed": project.company_managed,
            "created_by_role_id": project.created_by_role_id,
            "created_by_role": project.created_by_role,
            "created_by_person": created_by_person,
            "created_at": safe_isoformat(project.created_at),
            "sprints": sprints
        }
        return jsonify({"project": result, "status": 1}), 200
    except Exception as e:
        return jsonify({"success": 0, "error": str(e)}), 500

def update_project(project_id, decoded_payload=None):
    try:
        project = Project.query.get(project_id)
        if not project:
            return jsonify({"message": "Project not found", "status": 0}), 404

        data = request.get_json()
        
        if "client_id" in data:
            project.client_id = data["client_id"]
        if "group_id" in data:
            project.group_id = data["group_id"]
        if "name" in data:
            project.name = data["name"].strip() if data["name"] else None
        if "description" in data:
            project.description = data["description"].strip() if data["description"] else None
        if "start_date" in data:
            project.start_date = parse_date(data["start_date"])
        if "end_date" in data:
            project.end_date = parse_date(data["end_date"])
        if "status" in data:
            project.status = data["status"]
        if "project_logo" in data:
            project_logo = data.get("project_logo")
            saved_logo_url = save_image(project_logo, folder="project_logos")
            project.project_logo = saved_logo_url if saved_logo_url else project_logo
        if "remark" in data:
            project.remark = data["remark"].strip() if data["remark"] else None
        if "by_tl_managed" in data:
            project.by_tl_managed = data["by_tl_managed"]
        if "team_managed" in data:
            project.team_managed = data["team_managed"]
        if "company_managed" in data:
            project.company_managed = data["company_managed"]

        err = touch_updated_at(project, request)
        if err:
            return err
            
        db.session.commit()
        return jsonify({"message": "Project updated successfully", "status": 1}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": 0, "error": str(e)}), 500

def delete_project(project_id, decoded_payload=None):
    try:
        project = Project.query.get(project_id)
        if not project:
            return jsonify({"msg": "Project not found", "status": 0}), 404
        
        # Check all associated records
        association_types = []
        
        # Check project allocations
        allocations = ProjectAllocation.query.filter_by(project_id=project_id).all()
        if allocations:
            association_types.append("Project Allocations")
        
        # Check project excel files
        from src.models.project_excel_model import ProjectExcel
        excels = ProjectExcel.query.filter_by(project_id=project_id).all()
        if excels:
            association_types.append("Excel Files")
        
        # Check tasks
        from src.models.task_model import Task
        tasks = Task.query.filter_by(project_id=project_id).all()
        if tasks:
            association_types.append("Tasks")
        
        # Check meetings
        from src.models.meeting_model import Meeting
        meetings = Meeting.query.filter_by(project_id=project_id).all()
        if meetings:
            association_types.append("Meetings")
        
        # If there are any associations, prevent deletion and return details
        if association_types:
            return jsonify({
                "msg": "Cannot delete project. It is associated with the following items: " + ", ".join(association_types),
                "status": 0,
                "association_types": association_types
            }), 400
            
        # If no associations, proceed with deletion
        db.session.delete(project)
        db.session.commit()
        return jsonify({"msg": "Project deleted successfully", "status": 1}), 200
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting project: {str(e)}")
        return jsonify({"success": 0, "msg": "Failed to delete project. Please try again later.", "status": 0}), 500
