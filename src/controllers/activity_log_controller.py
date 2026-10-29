from flask import jsonify, request
import datetime
import json
from src import db
from src.models.activity_log_model import ActivityLog
from src.utils.role_utils import get_person_details
from src.utils.date_utils import safe_isoformat

def create_activity_log(role_id, role, table_name, record_id, action, old_data=None, new_data=None, remark=None):
    """
    Helper function to create activity logs from other controllers.
    """
    try:
        ip_address = request.remote_addr if request else None
        user_agent = request.user_agent.string if request else None
        
        # Convert dict to JSON string if necessary
        old_data_str = json.dumps(old_data) if isinstance(old_data, dict) else old_data
        new_data_str = json.dumps(new_data) if isinstance(new_data, dict) else new_data

        log = ActivityLog(
            role_id=role_id,
            role=role,
            table_name=table_name,
            record_id=record_id,
            action=action,
            old_data=old_data_str,
            new_data=new_data_str,
            ip_address=ip_address,
            user_agent=user_agent,
            remark=remark
        )
        db.session.add(log)
        db.session.commit()
        return True
    except Exception as e:
        db.session.rollback()
        print(f"Error creating activity log: {e}")
        return False

def get_all_activity_logs(decoded_payload=None):
    try:
        logs = ActivityLog.query.order_by(ActivityLog.created_at.desc()).all()
        result = []
        for log in logs:
            person = get_person_details(log.role, log.role_id)
            result.append({
                "id": log.id,
                "role_id": log.role_id,
                "role": log.role,
                "person": person,
                "table_name": log.table_name,
                "record_id": log.record_id,
                "action": log.action,
                "old_data": json.loads(log.old_data) if log.old_data else None,
                "new_data": json.loads(log.new_data) if log.new_data else None,
                "ip_address": log.ip_address,
                "user_agent": log.user_agent,
                "remark": log.remark,
                "created_at": safe_isoformat(log.created_at)
            })
        return jsonify({"logs": result, "status": 1}), 200
    except Exception as e:
        return jsonify({"success": 0, "error": str(e)}), 500

def get_logs_by_role(role_id, role):
    try:
        logs = ActivityLog.query.filter_by(role_id=role_id, role=role).order_by(ActivityLog.created_at.desc()).all()
        result = []
        for log in logs:
            person = get_person_details(log.role, log.role_id)
            result.append({
                "id": log.id,
                "table_name": log.table_name,
                "record_id": log.record_id,
                "action": log.action,
                "person": person,
                "remark": log.remark,
                "created_at": safe_isoformat(log.created_at)
            })
        return jsonify({"logs": result, "status": 1}), 200
    except Exception as e:
        return jsonify({"success": 0, "error": str(e)}), 500

# Backward compatibility
def get_logs_by_user(user_id, decoded_payload=None):
    return get_logs_by_role(None, None)

def get_logs_by_table(table_name, decoded_payload=None):
    try:
        logs = ActivityLog.query.filter_by(table_name=table_name).order_by(ActivityLog.created_at.desc()).all()
        result = []
        for log in logs:
            person = get_person_details(log.role, log.role_id)
            result.append({
                "id": log.id,
                "role_id": log.role_id,
                "role": log.role,
                "person": person,
                "record_id": log.record_id,
                "action": log.action,
                "created_at": safe_isoformat(log.created_at)
            })
        return jsonify({"logs": result, "status": 1}), 200
    except Exception as e:
        return jsonify({"success": 0, "error": str(e)}), 500
