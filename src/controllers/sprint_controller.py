from flask import jsonify, request
from src import db
from src.models.sprint_model import Sprint
from src.models.project_model import Project
from src.utils.date_utils import safe_isoformat
from src.utils.project_permissions import (
    can_manage_project_sprints,
    restriction_message,
)


def create_sprint(decoded_payload=None):
    try:
        data = request.get_json()
        
        project_id = data.get("project_id")
        sprint_name = data.get("sprint_name")
        sprint_goal = data.get("sprint_goal")
        description = data.get("description")
        start_date = data.get("start_date")
        end_date = data.get("end_date")
        status = data.get("status", "PLANNED")
        is_active = data.get("is_active", True)
        created_by = decoded_payload.get("user_id") if decoded_payload else None

        if not project_id or not sprint_name or not start_date:
            return jsonify({"msg": "Project ID, Sprint Name, and Start Date are required", "status": 0}), 400

        project = Project.query.get(project_id)
        if not project:
            return jsonify({"message": "Project not found", "status": 0}), 404
        actor_role = decoded_payload.get("role") if decoded_payload else None
        if not can_manage_project_sprints(project, actor_role):
            return jsonify(
                {
                    "msg": restriction_message(project, "Creating sprints"),
                    "status": 0,
                    "restricted": True,
                }
            ), 403

        # Determine sprint_status based on status
        sprint_status = 0
        if status == "ACTIVE":
            sprint_status = 1
        elif status in ["COMPLETED", "CANCELLED"]:
            sprint_status = 2

        new_sprint = Sprint(
            project_id=project_id,
            sprint_name=sprint_name,
            sprint_goal=sprint_goal,
            description=description,
            start_date=start_date,
            end_date=end_date,
            status=status,
            is_active=is_active,
            sprint_status=sprint_status,
            created_by=created_by
        )
        db.session.add(new_sprint)
        db.session.commit()
        
        return jsonify({"msg": "Sprint created successfully", "status": 1, "id": new_sprint.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": 0, "error": str(e)}), 500

def get_all_sprints(decoded_payload=None):
    try:
        from src.models.task_model import Task
        
        project_id = request.args.get("project_id")
        query = Sprint.query
        
        if project_id:
            query = query.filter_by(project_id=project_id)
            
        sprints = query.order_by(Sprint.created_at.desc()).all()
        result = []
        for sprint in sprints:
            # Determine sprint_status if it's None
            sprint_status = sprint.sprint_status
            if sprint_status is None:
                if sprint.status == "ACTIVE":
                    sprint_status = 1
                elif sprint.status in ["COMPLETED", "CANCELLED"]:
                    sprint_status = 2
                else:
                    sprint_status = 0

            # Get task count and check for non-completed tasks
            task_count = Task.query.filter_by(sprint_id=sprint.id).count()
            
            # Check if there are any non-completed tasks (using is_completed flag on task_status)
            from src.models.task_status_model import TaskStatus
            non_completed_tasks = Task.query.join(
                TaskStatus, Task.status_id == TaskStatus.id
            ).filter(
                Task.sprint_id == sprint.id,
                TaskStatus.is_completed == False
            ).count()
            
            has_non_completed_tasks = non_completed_tasks > 0

            sprint_data = {
                "id": sprint.id,
                "project_id": sprint.project_id,
                "sprint_name": sprint.sprint_name,
                "sprint_goal": sprint.sprint_goal,
                "description": sprint.description,
                "start_date": safe_isoformat(sprint.start_date),
                "end_date": safe_isoformat(sprint.end_date),
                "status": sprint.status,
                "is_active": sprint.is_active,
                "sprint_status": sprint_status,
                "task_count": task_count,
                "has_non_completed_tasks": has_non_completed_tasks,
                "created_by": sprint.created_by,
                "updated_by": sprint.updated_by,
                "created_at": safe_isoformat(sprint.created_at),
                "updated_at": safe_isoformat(sprint.updated_at),
                "tasks": []
            }
            # Add tasks
            for task in sprint.tasks:
                sprint_data["tasks"].append({
                    "id": task.id,
                    "title": task.title,
                    "description": task.description,
                    "status_id": task.status_id,
                    "status_name": task.status.name if task.status else None
                })
            result.append(sprint_data)
        return jsonify({"sprints": result, "status": 1}), 200
    except Exception as e:
        return jsonify({"success": 0, "error": str(e)}), 500

def get_sprint_by_id(sprint_id, decoded_payload=None):
    try:
        sprint = Sprint.query.get(sprint_id)
        if not sprint:
            return jsonify({"message": "Sprint not found", "status": 0}), 404
        
        # Determine sprint_status if it's None
        sprint_status = sprint.sprint_status
        if sprint_status is None:
            if sprint.status == "ACTIVE":
                sprint_status = 1
            elif sprint.status in ["COMPLETED", "CANCELLED"]:
                sprint_status = 2
            else:
                sprint_status = 0

        result = {
            "id": sprint.id,
            "project_id": sprint.project_id,
            "sprint_name": sprint.sprint_name,
            "sprint_goal": sprint.sprint_goal,
            "description": sprint.description,
            "start_date": safe_isoformat(sprint.start_date),
            "end_date": safe_isoformat(sprint.end_date),
            "status": sprint.status,
            "is_active": sprint.is_active,
            "sprint_status": sprint_status,
            "created_by": sprint.created_by,
            "updated_by": sprint.updated_by,
            "created_at": safe_isoformat(sprint.created_at),
            "updated_at": safe_isoformat(sprint.updated_at),
            "tasks": []
        }
        # Add tasks
        for task in sprint.tasks:
            result["tasks"].append({
                "id": task.id,
                "title": task.title,
                "description": task.description,
                "status_id": task.status_id,
                "status_name": task.status.name if task.status else None
            })
        return jsonify({"sprint": result, "status": 1}), 200
    except Exception as e:
        return jsonify({"success": 0, "error": str(e)}), 500

def update_sprint(sprint_id, decoded_payload=None):
    try:
        sprint = Sprint.query.get(sprint_id)
        if not sprint:
            return jsonify({"message": "Sprint not found", "status": 0}), 404

        project = Project.query.get(sprint.project_id)
        actor_role = decoded_payload.get("role") if decoded_payload else None
        if not can_manage_project_sprints(project, actor_role):
            return jsonify(
                {
                    "msg": restriction_message(project, "Updating sprints"),
                    "status": 0,
                    "restricted": True,
                }
            ), 403

        data = request.get_json()
        
        if "project_id" in data:
            sprint.project_id = data["project_id"]
        if "sprint_name" in data:
            sprint.sprint_name = data["sprint_name"]
        if "sprint_goal" in data:
            sprint.sprint_goal = data["sprint_goal"]
        if "description" in data:
            sprint.description = data["description"]
        if "start_date" in data:
            sprint.start_date = data["start_date"]
        if "end_date" in data:
            sprint.end_date = data["end_date"]
        if "status" in data:
            sprint.status = data["status"]
        if "is_active" in data:
            sprint.is_active = data["is_active"]
        
        sprint.updated_by = decoded_payload.get("user_id") if decoded_payload else None
            
        db.session.commit()
        return jsonify({"message": "Sprint updated successfully", "status": 1}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": 0, "error": str(e)}), 500

def delete_sprint(sprint_id, decoded_payload=None):
    try:
        from src.models.task_model import Task
        
        sprint = Sprint.query.get(sprint_id)
        if not sprint:
            return jsonify({"message": "Sprint not found", "status": 0}), 404

        project = Project.query.get(sprint.project_id)
        actor_role = decoded_payload.get("role") if decoded_payload else None
        if not can_manage_project_sprints(project, actor_role):
            return jsonify(
                {
                    "msg": restriction_message(project, "Deleting sprints"),
                    "status": 0,
                    "restricted": True,
                }
            ), 403
            
        # Check if there are any tasks in this sprint
        task_count = Task.query.filter_by(sprint_id=sprint_id).count()
        if task_count > 0:
            return jsonify({"message": "Cannot delete sprint with tasks. Please move or delete tasks first.", "status": 0}), 400
            
        db.session.delete(sprint)
        db.session.commit()
        return jsonify({"message": "Sprint deleted successfully", "status": 1}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": 0, "error": str(e)}), 500

def start_sprint(sprint_id, decoded_payload=None):
    try:
        sprint = Sprint.query.get(sprint_id)
        if not sprint:
            return jsonify({"message": "Sprint not found", "status": 0}), 404
        
        # Check if there's already an active sprint for the project
        active_sprint = Sprint.query.filter(
            Sprint.project_id == sprint.project_id,
            (Sprint.sprint_status == 1) | (Sprint.status == "ACTIVE"),
            Sprint.id != sprint_id
        ).first()
        
        if active_sprint:
            return jsonify({"message": "There is already an active sprint for this project", "status": 0}), 400
        
        sprint.status = "ACTIVE"
        sprint.sprint_status = 1
        sprint.updated_by = decoded_payload.get("user_id") if decoded_payload else None
        
        db.session.commit()
        return jsonify({"message": "Sprint started successfully", "status": 1}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": 0, "error": str(e)}), 500

def end_sprint(sprint_id, decoded_payload=None):
    try:
        sprint = Sprint.query.get(sprint_id)
        if not sprint:
            return jsonify({"message": "Sprint not found", "status": 0}), 404
        
        # Check if sprint is active (either via sprint_status or status string)
        is_active = (sprint.sprint_status == 1) or (sprint.status == "ACTIVE")
        if not is_active:
            return jsonify({"message": "Only active sprints can be ended", "status": 0}), 400
        
        sprint.status = "COMPLETED"
        sprint.sprint_status = 2
        sprint.updated_by = decoded_payload.get("user_id") if decoded_payload else None
        
        db.session.commit()
        return jsonify({"message": "Sprint ended successfully", "status": 1}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": 0, "error": str(e)}), 500

def start_sprint_with_move(sprint_id, decoded_payload=None):
    try:
        from src.models.task_model import Task
        from src.models.task_status_model import TaskStatus
        
        new_sprint = Sprint.query.get(sprint_id)
        if not new_sprint:
            return jsonify({"message": "Sprint not found", "status": 0}), 404
        
        data = request.get_json()
        current_active_sprint_id = data.get("current_active_sprint_id")
        
        current_active_sprint = None
        if current_active_sprint_id:
            current_active_sprint = Sprint.query.get(current_active_sprint_id)
        
        # End current active sprint
        if current_active_sprint:
            current_active_sprint.status = "COMPLETED"
            current_active_sprint.sprint_status = 2
            current_active_sprint.updated_by = decoded_payload.get("user_id") if decoded_payload else None
        
        # Move all non-completed tasks from current active sprint to new sprint
        if current_active_sprint:
            # Get all tasks in current sprint
            all_tasks = Task.query.filter_by(sprint_id=current_active_sprint.id).all()
            for task in all_tasks:
                # Check if task is not completed (using task's status is_completed)
                task_status = TaskStatus.query.get(task.status_id)
                if not task_status or not task_status.is_completed:
                    # Move this task to new sprint
                    task.sprint_id = new_sprint.id
        
        # Start new sprint
        new_sprint.status = "ACTIVE"
        new_sprint.sprint_status = 1
        new_sprint.updated_by = decoded_payload.get("user_id") if decoded_payload else None
        
        db.session.commit()
        return jsonify({"message": "Sprint started successfully, tasks moved", "status": 1}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": 0, "error": str(e)}), 500
