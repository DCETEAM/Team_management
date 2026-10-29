from flask import jsonify, request
import datetime
from src import db
from src.models.sub_task_model import SubTask
from src.utils.role_utils import get_person_details
from src.utils.db_retry import db_retry
from src.utils.date_utils import safe_isoformat

@db_retry(max_retries=3)
def create_sub_task(decoded_payload=None):
    try:
        data = request.get_json()
        
        parent_task_id = data.get("parent_task_id")
        status_id = data.get("status_id")
        title = data.get("title")
        description = data.get("description")
        priority = data.get("priority", "medium")
        start_date_str = data.get("start_date")
        due_date_str = data.get("due_date")
        role_id = data.get("role_id")
        role = data.get("role")
        estimated_hours = data.get("estimated_hours")
        actual_hours = data.get("actual_hours")
        remark = data.get("remark")
        
        assigned_by_role_id = decoded_payload.get("role_id") if decoded_payload else None
        assigned_by_role = decoded_payload.get("role") if decoded_payload else None

        if not all([parent_task_id, status_id, title]):
            return jsonify({"msg": "Parent Task ID, Status ID, and Title are required", "status": 0}), 400
        

        try:
            start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else None
            due_date = datetime.datetime.strptime(due_date_str, '%Y-%m-%d').date() if due_date_str else None
        except ValueError:
            return jsonify({"msg": "Invalid date format. Use YYYY-MM-DD", "status": 0}), 400

        new_sub_task = SubTask(
            parent_task_id=parent_task_id,
            status_id=status_id,
            title=title,
            description=description,
            priority=priority,
            start_date=start_date,
            due_date=due_date,
            role_id=role_id,
            role=role,
            assigned_by_role_id=assigned_by_role_id,
            assigned_by_role=assigned_by_role,
            estimated_hours=estimated_hours,
            actual_hours=actual_hours,
            remark=remark
        )
        db.session.add(new_sub_task)
        db.session.commit()
        
        return jsonify({"msg": "SubTask created successfully", "status": 1, "sub_task_id": new_sub_task.id}), 201
    except Exception as e:
        print(str(e))
        db.session.rollback()
        if "MySQL server has gone away" in str(e):
            return create_sub_task(decoded_payload)
        else:
            return jsonify({"success": 0, "error": str(e)}), 500

@db_retry(max_retries=3)
def get_sub_tasks_by_task_id(task_id, decoded_payload=None):
    try:
        sub_tasks = SubTask.query.filter_by(parent_task_id=task_id).all()
        result = []
        for st in sub_tasks:
            assigned_by_person = get_person_details(st.assigned_by_role, st.assigned_by_role_id)
            assigned_person = get_person_details(st.role, st.role_id) if st.role_id and st.role else None
            result.append({
                "id": st.id,
                "parent_task_id": st.parent_task_id,
                "parent_task_title": st.parent_task.title if st.parent_task else None,
                "status_id": st.status_id,
                "status_name": st.status.name if st.status else None,
                "title": st.title,
                "description": st.description,
                "priority": st.priority,
                "start_date": safe_isoformat(st.start_date),
                "due_date": safe_isoformat(st.due_date),
                "role_id": st.role_id,
                "role": st.role,
                "assigned_person": assigned_person,
                "assigned_by_role_id": st.assigned_by_role_id,
                "assigned_by_role": st.assigned_by_role,
                "assigned_by_person": assigned_by_person,
                "estimated_hours": float(st.estimated_hours) if st.estimated_hours else None,
                "actual_hours": float(st.actual_hours) if st.actual_hours else None,
                "remark": st.remark,
                "created_at": st.created_at
            })
        return jsonify({"sub_tasks": result, "status": 1}), 200
    except Exception as e:
        if "MySQL server has gone away" in str(e):
            return get_sub_tasks_by_task_id(task_id, decoded_payload)
        else:
            return jsonify({"success": 0, "error": str(e)}), 500

@db_retry(max_retries=3)
def get_all_sub_tasks(decoded_payload=None):
    try:
        sub_tasks = SubTask.query.all()
        result = []
        for st in sub_tasks:
            assigned_by_person = get_person_details(st.assigned_by_role, st.assigned_by_role_id)
            assigned_person = get_person_details(st.role, st.role_id) if st.role_id and st.role else None
            result.append({
                "id": st.id,
                "parent_task_id": st.parent_task_id,
                "parent_task_title": st.parent_task.title if st.parent_task else None,
                "status_id": st.status_id,
                "status_name": st.status.name if st.status else None,
                "title": st.title,
                "description": st.description,
                "priority": st.priority,
                "start_date": safe_isoformat(st.start_date),
                "due_date": safe_isoformat(st.due_date),
                "role_id": st.role_id,
                "role": st.role,
                "assigned_person": assigned_person,
                "assigned_by_role_id": st.assigned_by_role_id,
                "assigned_by_role": st.assigned_by_role,
                "assigned_by_person": assigned_by_person,
                "estimated_hours": float(st.estimated_hours) if st.estimated_hours else None,
                "actual_hours": float(st.actual_hours) if st.actual_hours else None,
                "remark": st.remark,
                "created_at": st.created_at
            })
        return jsonify({"sub_tasks": result, "status": 1}), 200
    except Exception as e:
        if "MySQL server has gone away" in str(e):
            return get_all_sub_tasks(decoded_payload)
        else:
            return jsonify({"success": 0, "error": str(e)}), 500

@db_retry(max_retries=3)
def get_sub_task_by_id(sub_task_id, decoded_payload=None):
    try:
        st = SubTask.query.get(sub_task_id)
        if not st:
            return jsonify({"message": "SubTask not found", "status": 0}), 404
        
        assigned_by_person = get_person_details(st.assigned_by_role, st.assigned_by_role_id)
        assigned_person = get_person_details(st.role, st.role_id) if st.role_id and st.role else None
        result = {
            "id": st.id,
            "parent_task_id": st.parent_task_id,
            "parent_task_title": st.parent_task.title if st.parent_task else None,
            "status_id": st.status_id,
            "status_name": st.status.name if st.status else None,
            "title": st.title,
            "description": st.description,
            "priority": st.priority,
            "start_date": safe_isoformat(st.start_date),
            "due_date": safe_isoformat(st.due_date),
            "role_id": st.role_id,
            "role": st.role,
            "assigned_person": assigned_person,
            "assigned_by_role_id": st.assigned_by_role_id,
            "assigned_by_role": st.assigned_by_role,
            "assigned_by_person": assigned_by_person,
            "estimated_hours": float(st.estimated_hours) if st.estimated_hours else None,
            "actual_hours": float(st.actual_hours) if st.actual_hours else None,
            "remark": st.remark,
            "created_at": st.created_at
        }
        return jsonify({"sub_task": result, "status": 1}), 200
    except Exception as e:
        if "MySQL server has gone away" in str(e):
            return get_sub_task_by_id(sub_task_id, decoded_payload)
        else:
            return jsonify({"success": 0, "error": str(e)}), 500

@db_retry(max_retries=3)
def update_sub_task(sub_task_id, decoded_payload=None):
    try:
        st = SubTask.query.get(sub_task_id)
        if not st:
            return jsonify({"message": "SubTask not found", "status": 0}), 404

        data = request.get_json()
        
        if "parent_task_id" in data:
            st.parent_task_id = data["parent_task_id"]
        if "status_id" in data:
            st.status_id = data["status_id"]
        if "title" in data:
            st.title = data["title"]
        if "description" in data:
            st.description = data["description"]
        if "priority" in data:
            st.priority = data["priority"]
        if "start_date" in data:
            st.start_date = datetime.datetime.strptime(data["start_date"], '%Y-%m-%d').date() if data["start_date"] else None
        if "due_date" in data:
            st.due_date = datetime.datetime.strptime(data["due_date"], '%Y-%m-%d').date() if data["due_date"] else None
        if "role_id" in data:
            st.role_id = data["role_id"]
        if "role" in data:
            st.role = data["role"]
        if "estimated_hours" in data:
            st.estimated_hours = data["estimated_hours"]
        if "actual_hours" in data:
            st.actual_hours = data["actual_hours"]
        if "remark" in data:
            st.remark = data["remark"]
            
        db.session.commit()
        return jsonify({"message": "SubTask updated successfully", "status": 1}), 200
    except Exception as e:
        db.session.rollback()
        if "MySQL server has gone away" in str(e):
            return update_sub_task(sub_task_id, decoded_payload)
        else:
            return jsonify({"success": 0, "error": str(e)}), 500

@db_retry(max_retries=3)
def delete_sub_task(sub_task_id, decoded_payload=None):
    try:
        st = SubTask.query.get(sub_task_id)
        if not st:
            return jsonify({"message": "SubTask not found", "status": 0}), 404
            
        db.session.delete(st)
        db.session.commit()
        return jsonify({"message": "SubTask deleted successfully", "status": 1}), 200
    except Exception as e:
        db.session.rollback()
        if "MySQL server has gone away" in str(e):
            return delete_sub_task(sub_task_id, decoded_payload)
        else:
            return jsonify({"success": 0, "error": str(e)}), 500
