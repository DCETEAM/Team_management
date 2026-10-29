from flask import jsonify, request
import datetime
from src import db
from src.models.leave_request_model import LeaveRequest, LeaveRequestAudit
from src.utils.role_utils import get_person_details
from werkzeug.utils import secure_filename
import os
from src.utils.date_utils import safe_isoformat
from config import Config


def create_audit_log(leave_id, action, old_status, new_status, role_id, role, comment=None):
    audit = LeaveRequestAudit(
        leave_request_id=leave_id,
        action=action,
        old_status=old_status,
        new_status=new_status,
        performed_by_role_id=role_id,
        performed_by_role=role,
        comment=comment
    )
    db.session.add(audit)


def create_leave_request(decoded_payload):
    try:
        data = request.get_json()
        
        role_id = decoded_payload.get("role_id")
        role = decoded_payload.get("role")
        leave_type = data.get("type")  # leave | permission
        leave_subtype = data.get("leave_subtype")  # full_day | half_day (only for leave)
        reason = data.get("reason")
        start_date_str = data.get("start_date")
        end_date_str = data.get("end_date")
        start_time_str = data.get("start_time")
        end_time_str = data.get("end_time")
        attachment_path = data.get("attachment_path")
        remark = data.get("remark")

        if not all([leave_type, reason, start_date_str, end_date_str]):
            return jsonify({"msg": "Type, Reason, Start Date, and End Date are required", "status": 0}), 400

        if leave_type == "leave" and not leave_subtype:
            return jsonify({"msg": "Leave subtype is required (full_day or half_day)", "status": 0}), 400

        try:
            start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d').date()
            start_time = datetime.datetime.strptime(start_time_str, '%H:%M').time() if start_time_str else None
            end_time = datetime.datetime.strptime(end_time_str, '%H:%M').time() if end_time_str else None
        except ValueError:
            return jsonify({"msg": "Invalid date or time format. Use YYYY-MM-DD for date and HH:MM for time", "status": 0}), 400

        # Auto-convert permission > 1 hour to half-day leave
        converted_to_leave = False
        if leave_type == "permission" and start_time and end_time:
            start_dt = datetime.datetime.combine(start_date, start_time)
            end_dt = datetime.datetime.combine(end_date, end_time)
            duration_hours = (end_dt - start_dt).total_seconds() / 3600
            if duration_hours > 1:
                leave_type = "leave"
                leave_subtype = "half_day"
                converted_to_leave = True

        # Auto-approve superadmin requests
        initial_status = "pending"
        if role == "superadmin":
            initial_status = "approved"

        new_leave = LeaveRequest(
            role_id=role_id,
            role=role,
            type=leave_type,
            leave_subtype=leave_subtype,
            reason=reason,
            start_date=start_date,
            end_date=end_date,
            start_time=start_time,
            end_time=end_time,
            attachment_path=attachment_path,
            remark=remark,
            status=initial_status
        )
        db.session.add(new_leave)
        db.session.flush()

        # Create audit log
        create_audit_log(
            leave_id=new_leave.id,
            action="created",
            old_status=None,
            new_status=initial_status,
            role_id=role_id,
            role=role
        )

        db.session.commit()
        
        response_msg = "Leave request submitted successfully"
        if converted_to_leave:
            response_msg = "Request duration exceeded 1 hour, converted to Half-Day Leave and submitted successfully"

        return jsonify({"msg": response_msg, "status": 1, "leave_id": new_leave.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": 0, "error": str(e)}), 500


def get_all_leave_requests(decoded_payload):
    try:
        user_role = decoded_payload.get("role")
        user_role_id = decoded_payload.get("role_id")
        
        query = LeaveRequest.query
        
        # Filter based on user role
        if user_role in ["worker", "team_leader"]:
            # Workers and team leaders can only see their own requests
            query = query.filter_by(role_id=user_role_id, role=user_role)
        elif user_role in ["admin", "scrum"]:
            # Admins and scrums can see requests from workers/team leaders, and their own
            query = query.filter(
                (LeaveRequest.role.in_(["worker", "team_leader"])) |
                ((LeaveRequest.role == user_role) & (LeaveRequest.role_id == user_role_id))
            )
        # Superadmins see all
        
        leaves = query.order_by(LeaveRequest.created_at.desc()).all()
        result = []
        for leave in leaves:
            person = get_person_details(leave.role, leave.role_id)
            reviewed_by_person = get_person_details(leave.reviewed_by_role, leave.reviewed_by_role_id) if leave.reviewed_by_role_id and leave.reviewed_by_role else None
            result.append({
                "id": leave.id,
                "role_id": leave.role_id,
                "role": leave.role,
                "person": person,
                "type": leave.type,
                "leave_subtype": leave.leave_subtype,
                "reason": leave.reason,
                "start_date": safe_isoformat(leave.start_date),
                "end_date": safe_isoformat(leave.end_date),
                "start_time": leave.start_time.strftime('%H:%M') if leave.start_time else None,
                "end_time": leave.end_time.strftime('%H:%M') if leave.end_time else None,
                "attachment_path": leave.attachment_path,
                "status": leave.status,
                "reviewed_by_role_id": leave.reviewed_by_role_id,
                "reviewed_by_role": leave.reviewed_by_role,
                "reviewed_by_person": reviewed_by_person,
                "reviewed_at": safe_isoformat(leave.reviewed_at),
                "review_comment": leave.review_comment,
                "remark": leave.remark,
                "created_at": safe_isoformat(leave.created_at)
            })
        return jsonify({"leaves": result, "status": 1}), 200
    except Exception as e:
        return jsonify({"success": 0, "error": str(e)}), 500


def get_my_leave_requests(decoded_payload):
    try:
        role_id = decoded_payload.get("role_id")
        role = decoded_payload.get("role")
        leaves = LeaveRequest.query.filter_by(role_id=role_id, role=role).order_by(LeaveRequest.created_at.desc()).all()
        result = []
        for leave in leaves:
            person = get_person_details(leave.role, leave.role_id)
            reviewed_by_person = get_person_details(leave.reviewed_by_role, leave.reviewed_by_role_id) if leave.reviewed_by_role_id and leave.reviewed_by_role else None
            result.append({
                "id": leave.id,
                "role_id": leave.role_id,
                "role": leave.role,
                "person": person,
                "type": leave.type,
                "leave_subtype": leave.leave_subtype,
                "reason": leave.reason,
                "start_date": safe_isoformat(leave.start_date),
                "end_date": safe_isoformat(leave.end_date),
                "start_time": leave.start_time.strftime('%H:%M') if leave.start_time else None,
                "end_time": leave.end_time.strftime('%H:%M') if leave.end_time else None,
                "attachment_path": leave.attachment_path,
                "status": leave.status,
                "reviewed_by_person": reviewed_by_person,
                "review_comment": leave.review_comment,
                "created_at": safe_isoformat(leave.created_at)
            })
        return jsonify({"leaves": result, "status": 1}), 200
    except Exception as e:
        return jsonify({"success": 0, "error": str(e)}), 500


def get_leave_request_by_id(leave_id, decoded_payload):
    try:
        leave = LeaveRequest.query.get(leave_id)
        if not leave:
            return jsonify({"message": "Leave request not found", "status": 0}), 404
        
        # Check permission
        user_role = decoded_payload.get("role")
        user_role_id = decoded_payload.get("role_id")
        
        # Check if user is the requester
        is_owner = leave.role == user_role and leave.role_id == user_role_id
        
        # Check if user has approval permissions
        can_approve = False
        if user_role == "superadmin":
            can_approve = True
        elif user_role in ["admin", "scrum"]:
            if leave.role in ["worker", "team_leader"]:
                can_approve = True
        
        if not is_owner and not can_approve:
            return jsonify({"message": "Permission denied", "status": 0}), 403
        
        # Get audit logs
        audits = LeaveRequestAudit.query.filter_by(leave_request_id=leave_id).order_by(LeaveRequestAudit.performed_at.desc()).all()
        audit_logs = []
        for audit in audits:
            performed_by = get_person_details(audit.performed_by_role, audit.performed_by_role_id)
            audit_logs.append({
                "id": audit.id,
                "action": audit.action,
                "old_status": audit.old_status,
                "new_status": audit.new_status,
                "performed_by": performed_by,
                "performed_at": safe_isoformat(audit.performed_at),
                "comment": audit.comment
            })
        
        person = get_person_details(leave.role, leave.role_id)
        reviewed_by_person = get_person_details(leave.reviewed_by_role, leave.reviewed_by_role_id) if leave.reviewed_by_role_id and leave.reviewed_by_role else None
        
        result = {
            "id": leave.id,
            "role_id": leave.role_id,
            "role": leave.role,
            "person": person,
            "type": leave.type,
            "leave_subtype": leave.leave_subtype,
            "reason": leave.reason,
            "start_date": safe_isoformat(leave.start_date),
            "end_date": safe_isoformat(leave.end_date),
            "start_time": leave.start_time.strftime('%H:%M') if leave.start_time else None,
            "end_time": leave.end_time.strftime('%H:%M') if leave.end_time else None,
            "attachment_path": leave.attachment_path,
            "status": leave.status,
            "reviewed_by_role_id": leave.reviewed_by_role_id,
            "reviewed_by_role": leave.reviewed_by_role,
            "reviewed_by_person": reviewed_by_person,
            "reviewed_at": safe_isoformat(leave.reviewed_at),
            "review_comment": leave.review_comment,
            "remark": leave.remark,
            "created_at": safe_isoformat(leave.created_at),
            "audit_logs": audit_logs
        }
        
        return jsonify({"leave": result, "status": 1}), 200
    except Exception as e:
        return jsonify({"success": 0, "error": str(e)}), 500


def review_leave_request(leave_id, decoded_payload):
    try:
        leave = LeaveRequest.query.get(leave_id)
        if not leave:
            return jsonify({"message": "Leave request not found", "status": 0}), 404
        
        if leave.status != "pending":
            return jsonify({"message": "Only pending requests can be reviewed", "status": 0}), 400
        
        # Check approval permissions
        user_role = decoded_payload.get("role")
        user_role_id = decoded_payload.get("role_id")
        
        can_approve = False
        if user_role == "superadmin":
            can_approve = True
        elif user_role in ["admin", "scrum"]:
            if leave.role in ["worker", "team_leader"]:
                can_approve = True
        
        if not can_approve:
            return jsonify({"message": "You don't have permission to review this request", "status": 0}), 403
        
        data = request.get_json()
        status = data.get("status")  # approved | rejected
        review_comment = data.get("review_comment")
        
        if status not in ['approved', 'rejected']:
            return jsonify({"msg": "Status must be 'approved' or 'rejected'", "status": 0}), 400
            
        old_status = leave.status
        leave.status = status
        leave.review_comment = review_comment
        leave.reviewed_by_role_id = user_role_id
        leave.reviewed_by_role = user_role
        leave.reviewed_at = datetime.datetime.utcnow()
        
        # Create audit log
        create_audit_log(
            leave_id=leave_id,
            action=status,
            old_status=old_status,
            new_status=status,
            role_id=user_role_id,
            role=user_role,
            comment=review_comment
        )
        
        db.session.commit()
        return jsonify({"msg": f"Leave request {status} successfully", "status": 1}), 200
    except Exception as e:
        import traceback
        print(f"Error reviewing leave request: {str(e)}")
        print(traceback.format_exc())
        db.session.rollback()
        return jsonify({"success": 0, "error": str(e)}), 500


def cancel_leave_request(leave_id, decoded_payload):
    try:
        leave = LeaveRequest.query.get(leave_id)
        if not leave:
            return jsonify({"message": "Leave request not found", "status": 0}), 404
        
        if leave.status != "pending":
            return jsonify({"message": "Only pending requests can be cancelled", "status": 0}), 400
        
        # Check if user is the owner
        user_role = decoded_payload.get("role")
        user_role_id = decoded_payload.get("role_id")
        if leave.role != user_role or leave.role_id != user_role_id:
            return jsonify({"message": "You can only cancel your own requests", "status": 0}), 403
        
        old_status = leave.status
        leave.status = "cancelled"
        
        # Create audit log
        create_audit_log(
            leave_id=leave_id,
            action="cancelled",
            old_status=old_status,
            new_status="cancelled",
            role_id=user_role_id,
            role=user_role
        )
        
        db.session.commit()
        return jsonify({"msg": "Leave request cancelled successfully", "status": 1}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": 0, "error": str(e)}), 500


def delete_leave_request(leave_id, decoded_payload):
    try:
        leave = LeaveRequest.query.get(leave_id)
        if not leave:
            return jsonify({"message": "Leave request not found", "status": 0}), 404
        
        # Check if user is the owner or superadmin
        user_role = decoded_payload.get("role")
        user_role_id = decoded_payload.get("role_id")
        is_owner = leave.role == user_role and leave.role_id == user_role_id
        
        if not is_owner:
            return jsonify({"message": "Permission denied", "status": 0}), 403
        
        # Check status permissions
        is_superadmin = user_role == "superadmin"
        if not is_superadmin and leave.status != "pending":
            return jsonify({"message": "Only pending requests can be deleted", "status": 0}), 400
        if is_superadmin and leave.status not in ["pending", "approved"]:
            return jsonify({"message": "Only pending or approved requests can be deleted by superadmin", "status": 0}), 400
        
        # Delete audit logs first
        LeaveRequestAudit.query.filter_by(leave_request_id=leave_id).delete()
        
        db.session.delete(leave)
        db.session.commit()
        return jsonify({"msg": "Leave request deleted successfully", "status": 1}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": 0, "error": str(e)}), 500


def upload_attachment(decoded_payload):
    try:
        if 'file' not in request.files:
            return jsonify({"msg": "No file provided", "status": 0}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({"msg": "No file selected", "status": 0}), 400
        
        if file:
            filename = secure_filename(file.filename)
            # Add timestamp to filename to avoid conflicts
            timestamp = datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S')
            unique_filename = f"{timestamp}_{filename}"
            
            # Ensure attachments directory exists
            attachments_dir = Config.UPLOAD_FOLDER if hasattr(Config, 'UPLOAD_FOLDER') else os.path.join(os.path.dirname(__file__), '..', 'assets', 'attachments')
            os.makedirs(attachments_dir, exist_ok=True)
            
            file_path = os.path.join(attachments_dir, unique_filename)
            file.save(file_path)
            
            # Return the relative path
            relative_path = f"src/assets/attachments/{unique_filename}"
            return jsonify({"msg": "File uploaded successfully", "status": 1, "path": relative_path}), 200
    except Exception as e:
        return jsonify({"success": 0, "error": str(e)}), 500
