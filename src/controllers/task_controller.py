from flask import jsonify, request
import datetime
from src import db
from src.models.task_model import Task
from src.models.task_status_model import TaskStatus
from src.models.sprint_model import Sprint
from src.models.project_model import Project
from src.models.project_group_model import ProjectGroup
from src.utils.date_utils import parse_date, safe_isoformat
from src.utils.role_utils import get_person_details
from src.utils.db_retry import db_retry
from src.utils.project_permissions import (
    can_modify_project_tasks,
    can_move_task_to_status,
    can_manage_project_sprints,
    restriction_message,
)
from src.controllers.task_status_history_controller import record_task_status_change

@db_retry(max_retries=3)
def create_task(decoded_payload=None):
    try:
        data = request.get_json()
        print("create_task data:", data)
        
        project_id = data.get("project_id")
        sprint_id = data.get("sprint_id")
        allocation_id = data.get("allocation_id")
        status_id = data.get("status_id")
        title = data.get("title")
        description = data.get("description")
        goal = data.get("goal")
        priority = data.get("priority", "medium")
        start_date_str = data.get("start_date")
        due_date_str = data.get("due_date")
        # Handle both members (new) and worker_ids (old)
        members = data.get("members", [])
        worker_ids = data.get("worker_ids", [])
        if worker_ids and not members:
            members = worker_ids
        estimated_hours = data.get("estimated_hours")
        actual_hours = data.get("actual_hours")
        remark = data.get("remark")
        
        # Get assigned_by from:
        # 1. First check data for assigned_by_role_id and assigned_by_role (sent by frontend)
        # 2. Then check decoded_payload (JWT)
        # 3. Then fall back to old format (assigned_by user id)
        assigned_by_role_id = data.get("assigned_by_role_id")
        assigned_by_role = data.get("assigned_by_role")
        
        if not assigned_by_role_id or not assigned_by_role:
            if decoded_payload:
                print("Using decoded_payload:", decoded_payload)
                assigned_by_role_id = decoded_payload.get("role_id")
                assigned_by_role = decoded_payload.get("role")
        
        # Fallback to old format if needed
        assigned_by_user_id = data.get("assigned_by")
        print("assigned_by_user_id:", assigned_by_user_id)
        if (not assigned_by_role_id or not assigned_by_role) and assigned_by_user_id:
            # Old format: try to determine role from user (backward compatibility)
            from src.models.user_model import User
            print("Looking up user with id:", assigned_by_user_id)
            user = User.query.get(assigned_by_user_id)
            print("Found user:", user)
            if user:
                assigned_by_role_id = user.role_id
                assigned_by_role = user.role
                print("Set assigned_by_role_id:", assigned_by_role_id, "assigned_by_role:", assigned_by_role)
        
        print("project_id:", project_id)
        print("status_id:", status_id)
        print("title:", title)
        print("assigned_by_role_id:", assigned_by_role_id)
        print("assigned_by_role:", assigned_by_role)
        
        if not all([project_id, status_id, title, assigned_by_role_id, assigned_by_role]):
            return jsonify({"msg": "Project, Status, Title, and Assigner are required", "status": 0}), 400

        project = Project.query.get(project_id)
        if not project:
            return jsonify({"message": "Project not found", "status": 0}), 404
        actor_role = assigned_by_role or (decoded_payload.get("role") if decoded_payload else None)
        if not can_modify_project_tasks(project, actor_role):
            return jsonify(
                {
                    "msg": restriction_message(project, "Creating tasks"),
                    "status": 0,
                    "restricted": True,
                }
            ), 403

        start_date = parse_date(start_date_str) if start_date_str else None
        due_date = parse_date(due_date_str) if due_date_str else None
        
        created_task_ids = []
        
        # If there are members, create a separate task for each member
        if members and len(members) > 0:
            for member in members:
                # Wrap single member in a list for the task
                task_members = [member]
                
                new_task = Task(
                    project_id=project_id,
                    sprint_id=sprint_id,
                    allocation_id=allocation_id,
                    status_id=status_id,
                    title=title,
                    description=description,
                    goal=goal,
                    priority=priority,
                    start_date=start_date,
                    due_date=due_date,
                    members=task_members,
                    worker_ids=[member] if worker_ids else None, # Backward compatibility
                    assigned_by_role_id=assigned_by_role_id,
                    assigned_by_role=assigned_by_role,
                    assigned_by=assigned_by_user_id if assigned_by_user_id else None, # Backward compatibility
                    estimated_hours=estimated_hours,
                    actual_hours=actual_hours,
                    remark=remark
                )
                db.session.add(new_task)
                db.session.flush()
                created_task_ids.append(new_task.id)
        else:
            # If no members, create single task
            new_task = Task(
                project_id=project_id,
                sprint_id=sprint_id,
                allocation_id=allocation_id,
                status_id=status_id,
                title=title,
                description=description,
                goal=goal,
                priority=priority,
                start_date=start_date,
                due_date=due_date,
                members=members,
                worker_ids=worker_ids if worker_ids else None, # Backward compatibility
                assigned_by_role_id=assigned_by_role_id,
                assigned_by_role=assigned_by_role,
                assigned_by=assigned_by_user_id if assigned_by_user_id else None, # Backward compatibility
                estimated_hours=estimated_hours,
                actual_hours=actual_hours,
                remark=remark
            )
            db.session.add(new_task)
            db.session.flush()
            created_task_ids.append(new_task.id)
        
        db.session.commit()
        
        return jsonify({"msg": "Task(s) created successfully", "status": 1, "task_ids": created_task_ids}), 201
    except Exception as e:
        db.session.rollback()
        if "MySQL server has gone away" in str(e):
            return create_task(decoded_payload)
        else:
            return jsonify({"success": 0, "error": str(e)}), 500

@db_retry(max_retries=3)
def get_tasks_by_project(project_id, decoded_payload=None):
    try:
        tasks = Task.query.filter_by(project_id=project_id).all()
        
        result = []
        for task in tasks:
            # Calculate actual hours from subtasks if there are any
            total_actual_hours = None
            if task.sub_tasks and len(task.sub_tasks) > 0:
                total_actual_hours = 0.0
                for sub_task in task.sub_tasks:
                    if sub_task.actual_hours:
                        total_actual_hours += float(sub_task.actual_hours)
            else:
                total_actual_hours = float(task.actual_hours) if task.actual_hours else None
            
            # Enrich members
            enriched_members = []
            # Use task.worker_ids if available, else task.members (backward compatibility)
            task_members = task.worker_ids if task.worker_ids else task.members
            if task_members:
                for member in task_members:
                    member_role = member.get("role")
                    member_role_id = member.get("role_id")
                    user_id = member.get("user_id")
                    if member_role and member_role_id:
                        member_details = get_person_details(member_role, member_role_id)
                        if member_details:
                            enriched_members.append(member_details)
                        else:
                            enriched_members.append(member)
                    else:
                        enriched_members.append(member)
            
            assigned_by_person = get_person_details(task.assigned_by_role, task.assigned_by_role_id)
            task_data = {
                "id": task.id,
                "project_id": task.project_id,
                "project_name": task.project.name if task.project else None,
                "sprint_id": task.sprint_id,
                "sprint_name": task.sprint.sprint_name if task.sprint else None,
                "allocation_id": task.allocation_id,
                "status_id": task.status_id,
                "status_name": task.status.name if task.status else None,
                "title": task.title,
                "description": task.description,
                "goal": task.goal,
                "priority": task.priority,
                "start_date": safe_isoformat(task.start_date),
                "due_date": safe_isoformat(task.due_date),
                "assigned_by_role_id": task.assigned_by_role_id,
                "assigned_by_role": task.assigned_by_role,
                "assigned_by_person": assigned_by_person,
                "assigned_by": task.assigned_by, # Backward compatibility
                "worker_ids": task.worker_ids, # Backward compatibility
                "estimated_hours": float(task.estimated_hours) if task.estimated_hours else None,
                "actual_hours": total_actual_hours,
                "remark": task.remark,
                "created_at": task.created_at,
                "members": enriched_members
            }
            
            result.append(task_data)
        return jsonify({"tasks": result, "status": 1}), 200
    except Exception as e:
        import traceback
        print(f"Error in get_tasks_by_project: {str(e)}")
        print(traceback.format_exc())
        if "MySQL server has gone away" in str(e):
            return get_tasks_by_project(project_id, decoded_payload)
        else:
            return jsonify({"success": 0, "error": str(e)}), 500

@db_retry(max_retries=3)
def get_tasks_by_sprint(sprint_id, decoded_payload=None):
    try:
        tasks = Task.query.filter_by(sprint_id=sprint_id).all()
        
        result = []
        for task in tasks:
            # Calculate actual hours from subtasks if there are any
            total_actual_hours = None
            if task.sub_tasks and len(task.sub_tasks) > 0:
                total_actual_hours = 0.0
                for sub_task in task.sub_tasks:
                    if sub_task.actual_hours:
                        total_actual_hours += float(sub_task.actual_hours)
            else:
                total_actual_hours = float(task.actual_hours) if task.actual_hours else None
            
            # Enrich members
            enriched_members = []
            # Use task.worker_ids if available, else task.members (backward compatibility)
            task_members = task.worker_ids if task.worker_ids else task.members
            if task_members:
                for member in task_members:
                    member_role = member.get("role")
                    member_role_id = member.get("role_id")
                    user_id = member.get("user_id")
                    if member_role and member_role_id:
                        member_details = get_person_details(member_role, member_role_id)
                        if member_details:
                            enriched_members.append(member_details)
                        else:
                            enriched_members.append(member)
                    else:
                        enriched_members.append(member)
            
            assigned_by_person = get_person_details(task.assigned_by_role, task.assigned_by_role_id)
            task_data = {
                "id": task.id,
                "project_id": task.project_id,
                "project_name": task.project.name if task.project else None,
                "sprint_id": task.sprint_id,
                "sprint_name": task.sprint.sprint_name if task.sprint else None,
                "allocation_id": task.allocation_id,
                "status_id": task.status_id,
                "status_name": task.status.name if task.status else None,
                "title": task.title,
                "description": task.description,
                "goal": task.goal,
                "priority": task.priority,
                "start_date": safe_isoformat(task.start_date),
                "due_date": safe_isoformat(task.due_date),
                "assigned_by_role_id": task.assigned_by_role_id,
                "assigned_by_role": task.assigned_by_role,
                "assigned_by_person": assigned_by_person,
                "assigned_by": task.assigned_by, # Backward compatibility
                "worker_ids": task.worker_ids, # Backward compatibility
                "estimated_hours": float(task.estimated_hours) if task.estimated_hours else None,
                "actual_hours": total_actual_hours,
                "remark": task.remark,
                "created_at": task.created_at,
                "members": enriched_members
            }
            
            result.append(task_data)
        return jsonify({"tasks": result, "status": 1}), 200
    except Exception as e:
        import traceback
        print(f"Error in get_tasks_by_sprint: {str(e)}")
        print(traceback.format_exc())
        if "MySQL server has gone away" in str(e):
            return get_tasks_by_sprint(sprint_id, decoded_payload)
        else:
            return jsonify({"success": 0, "error": str(e)}), 500

@db_retry(max_retries=3)
def get_all_tasks(decoded_payload=None):
    try:
        tasks = Task.query.all()
        result = []
        for task in tasks:
            # Calculate actual hours from subtasks if there are any
            total_actual_hours = None
            if task.sub_tasks and len(task.sub_tasks) > 0:
                total_actual_hours = 0.0
                for sub_task in task.sub_tasks:
                    if sub_task.actual_hours:
                        total_actual_hours += float(sub_task.actual_hours)
            else:
                total_actual_hours = float(task.actual_hours) if task.actual_hours else None
            
            # Enrich members
            enriched_members = []
            # Use task.worker_ids if available, else task.members (backward compatibility)
            task_members = task.worker_ids if task.worker_ids else task.members
            if task_members:
                for member in task_members:
                    member_role = member.get("role")
                    member_role_id = member.get("role_id")
                    user_id = member.get("user_id")
                    if member_role and member_role_id:
                        member_details = get_person_details(member_role, member_role_id)
                        if member_details:
                            enriched_members.append(member_details)
                        else:
                            enriched_members.append(member)
                    else:
                        enriched_members.append(member)
            
            assigned_by_person = get_person_details(task.assigned_by_role, task.assigned_by_role_id)
            task_data = {
                "id": task.id,
                "project_id": task.project_id,
                "project_name": task.project.name if task.project else None,
                "sprint_id": task.sprint_id,
                "sprint_name": task.sprint.sprint_name if task.sprint else None,
                "allocation_id": task.allocation_id,
                "status_id": task.status_id,
                "status_name": task.status.name if task.status else None,
                "title": task.title,
                "description": task.description,
                "goal": task.goal,
                "priority": task.priority,
                "start_date": safe_isoformat(task.start_date),
                "due_date": safe_isoformat(task.due_date),
                "assigned_by_role_id": task.assigned_by_role_id,
                "assigned_by_role": task.assigned_by_role,
                "assigned_by_person": assigned_by_person,
                "assigned_by": task.assigned_by, # Backward compatibility
                "worker_ids": task.worker_ids, # Backward compatibility
                "estimated_hours": float(task.estimated_hours) if task.estimated_hours else None,
                "actual_hours": total_actual_hours,
                "remark": task.remark,
                "created_at": task.created_at,
                "members": enriched_members
            }
            result.append(task_data)
        return jsonify({"tasks": result, "status": 1}), 200
    except Exception as e:
        import traceback
        print(f"Error in get_all_tasks: {str(e)}")
        print(traceback.format_exc())
        if "MySQL server has gone away" in str(e):
            return get_all_tasks(decoded_payload)
        else:
            return jsonify({"success": 0, "error": str(e)}), 500

@db_retry(max_retries=3)
def get_task_by_id(task_id, decoded_payload=None):
    try:
        task = Task.query.get(task_id)
        if not task:
            return jsonify({"message": "Task not found", "status": 0}), 404
        
        # Calculate actual hours from subtasks if there are any
        total_actual_hours = None
        if task.sub_tasks and len(task.sub_tasks) > 0:
            total_actual_hours = 0.0
            for sub_task in task.sub_tasks:
                if sub_task.actual_hours:
                    total_actual_hours += float(sub_task.actual_hours)
        else:
            total_actual_hours = float(task.actual_hours) if task.actual_hours else None
        
        # Enrich members
        enriched_members = []
        # Use task.worker_ids if available, else task.members (backward compatibility)
        task_members = task.worker_ids if task.worker_ids else task.members
        if task_members:
            for member in task_members:
                member_role = member.get("role")
                member_role_id = member.get("role_id")
                user_id = member.get("user_id")
                if member_role and member_role_id:
                    member_details = get_person_details(member_role, member_role_id)
                    if member_details:
                        enriched_members.append(member_details)
                    else:
                        enriched_members.append(member)
                else:
                    enriched_members.append(member)
        
        assigned_by_person = get_person_details(task.assigned_by_role, task.assigned_by_role_id)
        result = {
            "id": task.id,
            "project_id": task.project_id,
            "project_name": task.project.name if task.project else None,
            "sprint_id": task.sprint_id,
            "sprint_name": task.sprint.sprint_name if task.sprint else None,
            "allocation_id": task.allocation_id,
            "status_id": task.status_id,
            "status_name": task.status.name if task.status else None,
            "title": task.title,
            "description": task.description,
            "goal": task.goal,
            "priority": task.priority,
            "start_date": safe_isoformat(task.start_date),
            "due_date": safe_isoformat(task.due_date),
            "assigned_by_role_id": task.assigned_by_role_id,
            "assigned_by_role": task.assigned_by_role,
            "assigned_by_person": assigned_by_person,
            "assigned_by": task.assigned_by, # Backward compatibility
            "worker_ids": task.worker_ids, # Backward compatibility
            "estimated_hours": float(task.estimated_hours) if task.estimated_hours else None,
            "actual_hours": total_actual_hours,
            "remark": task.remark,
            "created_at": task.created_at,
            "members": enriched_members
        }
        return jsonify({"task": result, "status": 1}), 200
    except Exception as e:
        import traceback
        print(f"Error in get_task_by_id: {str(e)}")
        print(traceback.format_exc())
        if "MySQL server has gone away" in str(e):
            return get_task_by_id(task_id, decoded_payload)
        else:
            return jsonify({"success": 0, "error": str(e)}), 500

@db_retry(max_retries=3)
def update_task(task_id, decoded_payload=None):
    try:
        task = Task.query.get(task_id)
        if not task:
            return jsonify({"message": "Task not found", "status": 0}), 404

        data = request.get_json()
        
        project = Project.query.get(task.project_id)
        actor_role = decoded_payload.get("role") if decoded_payload else None

        mutating_fields = {
            "project_id",
            "sprint_id",
            "allocation_id",
            "title",
            "description",
            "goal",
            "priority",
            "start_date",
            "due_date",
            "members",
            "worker_ids",
            "estimated_hours",
            "actual_hours",
            "remark",
        }
        is_status_only = "status_id" in data and not any(k in data for k in mutating_fields)

        if any(k in data for k in mutating_fields):
            if not can_modify_project_tasks(project, actor_role):
                return jsonify(
                    {
                        "msg": restriction_message(project, "Editing tasks"),
                        "status": 0,
                        "restricted": True,
                    }
                ), 403
        
        if "status_id" in data:
            new_status = TaskStatus.query.get(data["status_id"])
            old_status_id = task.status_id
            old_status = TaskStatus.query.get(old_status_id)

            if not can_move_task_to_status(actor_role, new_status):
                return jsonify(
                    {
                        "msg": "This status is confidential. Moving tasks here is restricted for workers.",
                        "status": 0,
                        "restricted": True,
                    }
                ), 403

            if new_status and new_status.is_completed:
                # Check if all subtasks are completed
                if task.sub_tasks and len(task.sub_tasks) > 0:
                    all_subtasks_completed = True
                    for sub_task in task.sub_tasks:
                        sub_task_status = TaskStatus.query.get(sub_task.status_id)
                        if not sub_task_status or not sub_task_status.is_completed:
                            all_subtasks_completed = False
                            break
                    if not all_subtasks_completed:
                        return jsonify({"message": "Cannot mark task as completed until all subtasks are completed", "status": 0}), 400
        
        if "project_id" in data:
            task.project_id = data["project_id"]
        if "sprint_id" in data:
            task.sprint_id = data["sprint_id"]
        if "allocation_id" in data:
            task.allocation_id = data["allocation_id"]
        if "status_id" in data:
            task.status_id = data["status_id"]
            if old_status_id != data["status_id"]:
                record_task_status_change(
                    task,
                    old_status_id,
                    data["status_id"],
                    old_status,
                    new_status,
                    decoded_payload,
                )
        if "title" in data:
            task.title = data["title"]
        if "description" in data:
            task.description = data["description"]
        if "goal" in data:
            task.goal = data["goal"]
        if "priority" in data:
            task.priority = data["priority"]
        if "start_date" in data:
            task.start_date = parse_date(data["start_date"])
        if "due_date" in data:
            task.due_date = parse_date(data["due_date"])
        if "members" in data:
            task.members = data["members"]
        if "worker_ids" in data:
            task.worker_ids = data["worker_ids"]
            if not task.members:
                task.members = data["worker_ids"]
        if "estimated_hours" in data:
            task.estimated_hours = data["estimated_hours"]
        if "actual_hours" in data:
            task.actual_hours = data["actual_hours"]
        if "remark" in data:
            task.remark = data["remark"]
            
        db.session.commit()
        return jsonify({"message": "Task updated successfully", "status": 1}), 200
    except Exception as e:
        db.session.rollback()
        if "MySQL server has gone away" in str(e):
            return update_task(task_id, decoded_payload)
        else:
            return jsonify({"success": 0, "error": str(e)}), 500

@db_retry(max_retries=3)
def delete_task(task_id, decoded_payload=None):
    try:
        task = Task.query.get(task_id)
        if not task:
            return jsonify({"message": "Task not found", "status": 0}), 404

        project = Project.query.get(task.project_id)
        actor_role = decoded_payload.get("role") if decoded_payload else None
        if not can_modify_project_tasks(project, actor_role):
            return jsonify(
                {
                    "msg": restriction_message(project, "Deleting tasks"),
                    "status": 0,
                    "restricted": True,
                }
            ), 403
        
        # First delete all sub-tasks
        from src.models.sub_task_model import SubTask
        SubTask.query.filter_by(parent_task_id=task_id).delete()
            
        db.session.delete(task)
        db.session.commit()
        return jsonify({"message": "Task deleted successfully", "status": 1}), 200
    except Exception as e:
        db.session.rollback()
        if "MySQL server has gone away" in str(e):
            return delete_task(task_id, decoded_payload)
        else:
            return jsonify({"success": 0, "error": str(e)}), 500

@db_retry(max_retries=3)
def get_dashboard_tasks(decoded_payload=None):
    try:
        # Fetch all project groups
        groups = ProjectGroup.query.all()
        
        # Also handle projects without a group
        ungrouped_projects = Project.query.filter_by(group_id=None).all()
        
        result = []
        
        # Process each group
        for group in groups:
            group_data = {
                "id": group.id,
                "name": group.name,
                "description": group.description,
                "projects": []
            }
            
            # Get all projects in this group
            for project in group.projects:
                project_data = {
                    "id": project.id,
                    "name": project.name,
                    "description": project.description,
                    "tasks": []
                }
                
                # Get all tasks for this project
                for task in project.tasks:
                    # Enrich members
                    enriched_members = []
                    # Use task.worker_ids if available, else task.members (backward compatibility)
                    task_members = task.worker_ids if task.worker_ids else task.members
                    print(f"Task {task.id} members: {task_members}")
                    if task_members:
                        for member in task_members:
                            print(f"Processing member: {member}")
                            # Handle both "type" and "role" fields
                            member_role = member.get("role") or member.get("type")
                            member_role_id = member.get("role_id")
                            user_id = member.get("user_id")
                            print(f"member_role: {member_role}, user_id: {user_id}")
                            
                            member_found = False
                            # If we have type and user_id, fetch directly from Worker or Admin table
                            if member_role and user_id:
                                print(f"Trying direct fetch with type {member_role} and user_id {user_id}")
                                member_details = None
                                if member_role in ["worker", "team_leader"]:
                                    from src.models.worker_model import Worker
                                    worker = Worker.query.get(user_id)
                                    print(f"Found worker: {worker}")
                                    if worker:
                                        member_details = {
                                            "role_id": user_id,
                                            "role": member_role,
                                            "first_name": worker.first_name,
                                            "last_name": worker.last_name,
                                            "email": worker.email,
                                            "avatar_url": worker.avatar_url
                                        }
                                elif member_role in ["superadmin", "admin", "scrum"]:
                                    from src.models.admin_model import Admin
                                    admin = Admin.query.get(user_id)
                                    print(f"Found admin: {admin}")
                                    if admin:
                                        member_details = {
                                            "role_id": user_id,
                                            "role": member_role,
                                            "first_name": admin.first_name,
                                            "last_name": admin.last_name,
                                            "email": admin.email,
                                            "avatar_url": admin.avatar_url
                                        }
                                
                                if member_details:
                                    print(f"Appending member details: {member_details}")
                                    enriched_members.append(member_details)
                                    member_found = True
                            
                            # If not found yet, try other methods
                            if not member_found:
                                # Handle case where we have user_id but not role_id
                                if user_id and not member_role_id:
                                    from src.models.user_model import User
                                    user = User.query.get(user_id)
                                    if user:
                                        member_role = user.role
                                        member_role_id = user.role_id
                                
                                if member_role and member_role_id:
                                    member_details = get_person_details(member_role, member_role_id)
                                    if member_details:
                                        print(f"Appending member details via get_person_details: {member_details}")
                                        enriched_members.append(member_details)
                                    else:
                                        print(f"No member details found via get_person_details, appending original: {member}")
                                        enriched_members.append(member)
                                else:
                                    print(f"No role and role_id found, appending original: {member}")
                                    enriched_members.append(member)
                    print(f"Enriched members: {enriched_members}")
                    
                    # Calculate actual hours from subtasks if there are any
                    total_actual_hours = None
                    if task.sub_tasks and len(task.sub_tasks) > 0:
                        total_actual_hours = 0.0
                        for sub_task in task.sub_tasks:
                            if sub_task.actual_hours:
                                total_actual_hours += float(sub_task.actual_hours)
                    else:
                        total_actual_hours = float(task.actual_hours) if task.actual_hours else None
                    
                    assigned_by_person = get_person_details(task.assigned_by_role, task.assigned_by_role_id)
                    task_data = {
                        "id": task.id,
                        "project_id": task.project_id,
                        "project_name": task.project.name if task.project else None,
                        "sprint_id": task.sprint_id,
                        "sprint_name": task.sprint.sprint_name if task.sprint else None,
                        "allocation_id": task.allocation_id,
                        "status_id": task.status_id,
                        "status_name": task.status.name if task.status else None,
                        "status_color": task.status.color if task.status else None,
                        "title": task.title,
                        "description": task.description,
                        "goal": task.goal,
                        "priority": task.priority,
                        "start_date": safe_isoformat(task.start_date),
                        "due_date": safe_isoformat(task.due_date),
                        "assigned_by_role_id": task.assigned_by_role_id,
                        "assigned_by_role": task.assigned_by_role,
                        "assigned_by_person": assigned_by_person,
                        "estimated_hours": float(task.estimated_hours) if task.estimated_hours else None,
                        "actual_hours": total_actual_hours,
                        "remark": task.remark,
                        "created_at": safe_isoformat(task.created_at),
                        "members": enriched_members
                    }
                    
                    project_data["tasks"].append(task_data)
                
                group_data["projects"].append(project_data)
            
            result.append(group_data)
        
        # Add ungrouped projects
        if ungrouped_projects:
            ungrouped_data = {
                "id": None,
                "name": "Ungrouped",
                "description": "Projects without a group",
                "projects": []
            }
            
            for project in ungrouped_projects:
                project_data = {
                    "id": project.id,
                    "name": project.name,
                    "description": project.description,
                    "tasks": []
                }
                
                # Get all tasks for this project
                for task in project.tasks:
                    # Enrich members
                    enriched_members = []
                    # Use task.worker_ids if available, else task.members (backward compatibility)
                    task_members = task.worker_ids if task.worker_ids else task.members
                    print(f"Task {task.id} members: {task_members}")
                    if task_members:
                        for member in task_members:
                            print(f"Processing member: {member}")
                            # Handle both "type" and "role" fields
                            member_role = member.get("role") or member.get("type")
                            member_role_id = member.get("role_id")
                            user_id = member.get("user_id")
                            print(f"member_role: {member_role}, user_id: {user_id}")
                            
                            member_found = False
                            # If we have type and user_id, fetch directly from Worker or Admin table
                            if member_role and user_id:
                                print(f"Trying direct fetch with type {member_role} and user_id {user_id}")
                                member_details = None
                                if member_role in ["worker", "team_leader"]:
                                    from src.models.worker_model import Worker
                                    worker = Worker.query.get(user_id)
                                    print(f"Found worker: {worker}")
                                    if worker:
                                        member_details = {
                                            "role_id": user_id,
                                            "role": member_role,
                                            "first_name": worker.first_name,
                                            "last_name": worker.last_name,
                                            "email": worker.email,
                                            "avatar_url": worker.avatar_url
                                        }
                                elif member_role in ["superadmin", "admin", "scrum"]:
                                    from src.models.admin_model import Admin
                                    admin = Admin.query.get(user_id)
                                    print(f"Found admin: {admin}")
                                    if admin:
                                        member_details = {
                                            "role_id": user_id,
                                            "role": member_role,
                                            "first_name": admin.first_name,
                                            "last_name": admin.last_name,
                                            "email": admin.email,
                                            "avatar_url": admin.avatar_url
                                        }
                                
                                if member_details:
                                    print(f"Appending member details: {member_details}")
                                    enriched_members.append(member_details)
                                    member_found = True
                            
                            # If not found yet, try other methods
                            if not member_found:
                                # Handle case where we have user_id but not role_id
                                if user_id and not member_role_id:
                                    from src.models.user_model import User
                                    user = User.query.get(user_id)
                                    if user:
                                        member_role = user.role
                                        member_role_id = user.role_id
                                
                                if member_role and member_role_id:
                                    member_details = get_person_details(member_role, member_role_id)
                                    if member_details:
                                        print(f"Appending member details via get_person_details: {member_details}")
                                        enriched_members.append(member_details)
                                    else:
                                        print(f"No member details found via get_person_details, appending original: {member}")
                                        enriched_members.append(member)
                                else:
                                    print(f"No role and role_id found, appending original: {member}")
                                    enriched_members.append(member)
                    print(f"Enriched members: {enriched_members}")
                    
                    # Calculate actual hours from subtasks if there are any
                    total_actual_hours = None
                    if task.sub_tasks and len(task.sub_tasks) > 0:
                        total_actual_hours = 0.0
                        for sub_task in task.sub_tasks:
                            if sub_task.actual_hours:
                                total_actual_hours += float(sub_task.actual_hours)
                    else:
                        total_actual_hours = float(task.actual_hours) if task.actual_hours else None
                    
                    assigned_by_person = get_person_details(task.assigned_by_role, task.assigned_by_role_id)
                    task_data = {
                        "id": task.id,
                        "project_id": task.project_id,
                        "project_name": task.project.name if task.project else None,
                        "sprint_id": task.sprint_id,
                        "sprint_name": task.sprint.sprint_name if task.sprint else None,
                        "allocation_id": task.allocation_id,
                        "status_id": task.status_id,
                        "status_name": task.status.name if task.status else None,
                        "status_color": task.status.color if task.status else None,
                        "title": task.title,
                        "description": task.description,
                        "goal": task.goal,
                        "priority": task.priority,
                        "start_date": safe_isoformat(task.start_date),
                        "due_date": safe_isoformat(task.due_date),
                        "assigned_by_role_id": task.assigned_by_role_id,
                        "assigned_by_role": task.assigned_by_role,
                        "assigned_by_person": assigned_by_person,
                        "estimated_hours": float(task.estimated_hours) if task.estimated_hours else None,
                        "actual_hours": total_actual_hours,
                        "remark": task.remark,
                        "created_at": safe_isoformat(task.created_at),
                        "members": enriched_members
                    }
                    
                    project_data["tasks"].append(task_data)
                
                ungrouped_data["projects"].append(project_data)
            
            result.append(ungrouped_data)
        
        return jsonify({"groups": result, "status": 1}), 200
    except Exception as e:
        import traceback
        print(f"Error in get_dashboard_tasks: {str(e)}")
        print(traceback.format_exc())
        if "MySQL server has gone away" in str(e):
            return get_dashboard_tasks(decoded_payload)
        else:
            return jsonify({"success": 0, "error": str(e)}), 500


@db_retry(max_retries=3)
def get_project_backlog(project_id, decoded_payload=None):
    try:
        # 1. Find the backlog status and todo status
        backlog_status = TaskStatus.query.filter_by(is_backlog=True).first()
        todo_status = TaskStatus.query.filter_by(is_todo=True).first()
        
        # Get all statuses first for status_map
        all_statuses = TaskStatus.query.order_by(TaskStatus.sort_order).all()
        status_map = {status.id: status for status in all_statuses}
        
        # 2. Get all backlog tasks for the project: tasks with no sprint_id and backlog status
        backlog_tasks_query = Task.query.filter_by(project_id=project_id, sprint_id=None)
        if backlog_status:
            backlog_tasks_query = backlog_tasks_query.filter_by(status_id=backlog_status.id)
        backlog_tasks = backlog_tasks_query.all()
        
        # Enrich backlog tasks
        enriched_backlog_tasks = []
        for task in backlog_tasks:
            # Enrich members
            enriched_members = []
            task_members = task.worker_ids if task.worker_ids else task.members
            if task_members:
                for member in task_members:
                    member_role = member.get("role") or member.get("type")
                    member_role_id = member.get("role_id")
                    user_id = member.get("user_id")
                    member_found = False
                    if member_role and user_id:
                        member_details = None
                        if member_role in ["worker", "team_leader"]:
                            from src.models.worker_model import Worker
                            worker = Worker.query.get(user_id)
                            if worker:
                                member_details = {
                                    "user_id": user_id,
                                    "role": member_role,
                                    "type": member_role,
                                    "first_name": worker.first_name,
                                    "last_name": worker.last_name,
                                    "email": worker.email,
                                    "avatar_url": worker.avatar_url
                                }
                        elif member_role in ["superadmin", "admin", "scrum"]:
                            from src.models.admin_model import Admin
                            admin = Admin.query.get(user_id)
                            if admin:
                                member_details = {
                                    "user_id": user_id,
                                    "role": member_role,
                                    "type": member_role,
                                    "first_name": admin.first_name,
                                    "last_name": admin.last_name,
                                    "email": admin.email,
                                    "avatar_url": admin.avatar_url
                                }
                        if member_details:
                            enriched_members.append(member_details)
                            member_found = True
                    if not member_found:
                        if user_id and not member_role_id:
                            from src.models.user_model import User
                            user = User.query.get(user_id)
                            if user:
                                member_role = user.role
                                member_role_id = user.role_id
                        if member_role and member_role_id:
                            member_details = get_person_details(member_role, member_role_id)
                            if member_details:
                                # Ensure user_id exists
                                if "user_id" not in member_details:
                                    member_details["user_id"] = member_details.get("role_id", user_id)
                                enriched_members.append(member_details)
                            else:
                                enriched_members.append(member)
                        else:
                            enriched_members.append(member)
            # Calculate actual hours from subtasks if there are any
            total_actual_hours = None
            if task.sub_tasks and len(task.sub_tasks) > 0:
                total_actual_hours = 0.0
                for sub_task in task.sub_tasks:
                    if sub_task.actual_hours:
                        total_actual_hours += float(sub_task.actual_hours)
            else:
                total_actual_hours = float(task.actual_hours) if task.actual_hours else None
            
            assigned_by_person = get_person_details(task.assigned_by_role, task.assigned_by_role_id)
            task_status = status_map.get(task.status_id)
            task_data = {
                "id": task.id,
                "task_id": task.id,
                "project_id": task.project_id,
                "project_name": task.project.name if task.project else None,
                "sprint_id": task.sprint_id,
                "sprint_name": task.sprint.sprint_name if task.sprint else None,
                "allocation_id": task.allocation_id,
                "status_id": task.status_id,
                "status_name": task_status.name if task_status else None,
                "status_color": task_status.color if task_status else None,
                "title": task.title,
                "description": task.description,
                "goal": task.goal,
                "priority": task.priority,
                "start_date": safe_isoformat(task.start_date),
                "due_date": safe_isoformat(task.due_date),
                "assigned_by_role_id": task.assigned_by_role_id,
                "assigned_by_role": task.assigned_by_role,
                "assigned_by_person": assigned_by_person,
                "assigned_by": task.assigned_by,
                "worker_ids": task.worker_ids,
                "assigned_workers": enriched_members,
                "estimated_hours": float(task.estimated_hours) if task.estimated_hours else None,
                "actual_hours": total_actual_hours,
                "remark": task.remark,
                "created_at": safe_isoformat(task.created_at),
                "members": enriched_members
            }
            enriched_backlog_tasks.append(task_data)
        
        # 3. Get all sprints for the project, each with their tasks
        sprints = Sprint.query.filter_by(project_id=project_id).order_by(Sprint.created_at.desc()).all()
        enriched_sprints = []
        for sprint in sprints:
            # Get all tasks for this sprint
            sprint_tasks = Task.query.filter_by(sprint_id=sprint.id).all()
            # Enrich sprint tasks
            enriched_sprint_tasks = []
            for task in sprint_tasks:
                task_members = task.worker_ids if task.worker_ids else task.members
                enriched_members = []
                if task_members:
                    for member in task_members:
                        member_role = member.get("role") or member.get("type")
                        member_role_id = member.get("role_id")
                        user_id = member.get("user_id")
                        member_found = False
                        if member_role and user_id:
                            member_details = None
                            if member_role in ["worker", "team_leader"]:
                                from src.models.worker_model import Worker
                                worker = Worker.query.get(user_id)
                                if worker:
                                    member_details = {
                                        "user_id": user_id,
                                        "role": member_role,
                                        "type": member_role,
                                        "first_name": worker.first_name,
                                        "last_name": worker.last_name,
                                        "email": worker.email,
                                        "avatar_url": worker.avatar_url
                                    }
                            elif member_role in ["superadmin", "admin", "scrum"]:
                                from src.models.admin_model import Admin
                                admin = Admin.query.get(user_id)
                                if admin:
                                    member_details = {
                                        "user_id": user_id,
                                        "role": member_role,
                                        "type": member_role,
                                        "first_name": admin.first_name,
                                        "last_name": admin.last_name,
                                        "email": admin.email,
                                        "avatar_url": admin.avatar_url
                                    }
                            if member_details:
                                enriched_members.append(member_details)
                                member_found = True
                    if not member_found:
                        if user_id and not member_role_id:
                            from src.models.user_model import User
                            user = User.query.get(user_id)
                            if user:
                                member_role = user.role
                                member_role_id = user.role_id
                        if member_role and member_role_id:
                            member_details = get_person_details(member_role, member_role_id)
                            if member_details:
                                # Ensure user_id exists
                                if "user_id" not in member_details:
                                    member_details["user_id"] = member_details.get("role_id", user_id)
                                enriched_members.append(member_details)
                            else:
                                enriched_members.append(member)
                        else:
                            enriched_members.append(member)
                assigned_by_person = get_person_details(task.assigned_by_role, task.assigned_by_role_id)
                task_status = status_map.get(task.status_id)
                task_data = {
                    "id": task.id,
                    "task_id": task.id,
                    "project_id": task.project_id,
                    "sprint_id": task.sprint_id,
                    "allocation_id": task.allocation_id,
                    "status_id": task.status_id,
                    "status_name": task_status.name if task_status else None,
                    "status_color": task_status.color if task_status else None,
                    "title": task.title,
                    "description": task.description,
                    "goal": task.goal,
                    "priority": task.priority,
                    "start_date": safe_isoformat(task.start_date),
                    "due_date": safe_isoformat(task.due_date),
                    "assigned_by_role_id": task.assigned_by_role_id,
                    "assigned_by_role": task.assigned_by_role,
                    "assigned_by_person": assigned_by_person,
                    "assigned_by": task.assigned_by,
                    "worker_ids": task.worker_ids,
                    "assigned_workers": enriched_members,
                    "estimated_hours": float(task.estimated_hours) if task.estimated_hours else None,
                    "actual_hours": float(task.actual_hours) if task.actual_hours else None,
                    "remark": task.remark,
                    "created_at": safe_isoformat(task.created_at),
                    "members": enriched_members
                }
                enriched_sprint_tasks.append(task_data)
            # Sprint data
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
                "created_by": sprint.created_by,
                "updated_by": sprint.updated_by,
                "created_at": safe_isoformat(sprint.created_at),
                "updated_at": safe_isoformat(sprint.updated_at),
                "tasks": enriched_sprint_tasks
            }
            enriched_sprints.append(sprint_data)
        
        return jsonify({
            "status": 1,
            "backlog_tasks": enriched_backlog_tasks,
            "sprints": enriched_sprints,
            "backlog_status": {
                "id": backlog_status.id,
                "name": backlog_status.name,
                "color": backlog_status.color
            } if backlog_status else None,
            "todo_status": {
                "id": todo_status.id,
                "name": todo_status.name,
                "color": todo_status.color
            } if todo_status else None
        }), 200
    except Exception as e:
        import traceback
        print(f"Error in get_project_backlog: {str(e)}")
        print(traceback.format_exc())
        if "MySQL server has gone away" in str(e):
            return get_project_backlog(project_id, decoded_payload)
        else:
            return jsonify({"success": 0, "error": str(e)}), 500
