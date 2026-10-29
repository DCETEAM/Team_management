from flask import jsonify, request
from src import db
from src.models.attendance_status_model import AttendanceStatus

def create_attendance_status(decoded_payload=None):
    try:
        data = request.get_json()
        
        status_name = data.get("status_name")
        status_code = data.get("status_code")
        is_present = data.get("is_present", False)
        is_absent = data.get("is_absent", False)
        is_active = data.get("is_active", True)

        if not status_name or not status_code:
            return jsonify({"msg": "Status name and status code are required", "status": 0}), 400

        if AttendanceStatus.query.filter_by(status_name=status_name).first():
            return jsonify({"msg": f"Status '{status_name}' already exists", "status": 0}), 409
        
        if AttendanceStatus.query.filter_by(status_code=status_code).first():
            return jsonify({"msg": f"Status code '{status_code}' already exists", "status": 0}), 409

        new_status = AttendanceStatus(
            status_name=status_name,
            status_code=status_code,
            is_present=is_present,
            is_absent=is_absent,
            is_active=is_active
        )
        db.session.add(new_status)
        db.session.commit()
        
        return jsonify({"msg": "Attendance status created successfully", "status": 1, "id": new_status.attendance_status_id}), 201
    except Exception as e:
        db.session.rollback()
        if "Duplicate entry" in str(e):
            if "status_name" in str(e):
                return jsonify({"msg": "Status name already exists", "status": 0}), 409
            if "status_code" in str(e):
                return jsonify({"msg": "Status code already exists", "status": 0}), 409
        return jsonify({"success": 0, "error": str(e)}), 500

def get_all_attendance_statuses(decoded_payload=None):
    try:
        statuses = AttendanceStatus.query.all()
        result = []
        for status in statuses:
            result.append({
                "attendance_status_id": status.attendance_status_id,
                "status_name": status.status_name,
                "status_code": status.status_code,
                "is_present": status.is_present,
                "is_absent": status.is_absent,
                "is_active": status.is_active,
                "created_at": status.created_at,
                "updated_at": status.updated_at
            })
        return jsonify({"attendance_statuses": result, "status": 1}), 200
    except Exception as e:
        return jsonify({"success": 0, "error": str(e)}), 500

def get_attendance_status_by_id(status_id, decoded_payload=None):
    try:
        status = AttendanceStatus.query.get(status_id)
        if not status:
            return jsonify({"message": "Attendance status not found", "status": 0}), 404
        
        result = {
            "attendance_status_id": status.attendance_status_id,
            "status_name": status.status_name,
            "status_code": status.status_code,
            "is_present": status.is_present,
            "is_absent": status.is_absent,
            "is_active": status.is_active,
            "created_at": status.created_at,
            "updated_at": status.updated_at
        }
        return jsonify({"attendance_status": result, "status": 1}), 200
    except Exception as e:
        return jsonify({"success": 0, "error": str(e)}), 500

def update_attendance_status(status_id, decoded_payload=None):
    try:
        status = AttendanceStatus.query.get(status_id)
        if not status:
            return jsonify({"message": "Attendance status not found", "status": 0}), 404

        data = request.get_json()
        
        if "status_name" in data:
            existing = AttendanceStatus.query.filter_by(status_name=data["status_name"]).first()
            if existing and existing.attendance_status_id != status_id:
                return jsonify({"msg": f"Status '{data['status_name']}' already exists", "status": 0}), 409
            status.status_name = data["status_name"]
        
        if "status_code" in data:
            existing = AttendanceStatus.query.filter_by(status_code=data["status_code"]).first()
            if existing and existing.attendance_status_id != status_id:
                return jsonify({"msg": f"Status code '{data['status_code']}' already exists", "status": 0}), 409
            status.status_code = data["status_code"]
        
        if "is_present" in data:
            status.is_present = data["is_present"]
        
        if "is_absent" in data:
            status.is_absent = data["is_absent"]
        
        if "is_active" in data:
            status.is_active = data["is_active"]
            
        db.session.commit()
        return jsonify({"message": "Attendance status updated successfully", "status": 1}), 200
    except Exception as e:
        db.session.rollback()
        if "Duplicate entry" in str(e):
            if "status_name" in str(e):
                return jsonify({"msg": "Status name already exists", "status": 0}), 409
            if "status_code" in str(e):
                return jsonify({"msg": "Status code already exists", "status": 0}), 409
        return jsonify({"success": 0, "error": str(e)}), 500

def delete_attendance_status(status_id, decoded_payload=None):
    try:
        status = AttendanceStatus.query.get(status_id)
        if not status:
            return jsonify({"message": "Attendance status not found", "status": 0}), 404
            
        db.session.delete(status)
        db.session.commit()
        return jsonify({"message": "Attendance status deleted successfully", "status": 1}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": 0, "error": str(e)}), 500
