from flask import jsonify, request
import datetime
from src import db
from src.models.meeting_model import Meeting
from src.utils.role_utils import get_person_details
from src.utils.db_retry import db_retry
from src.utils.date_utils import safe_isoformat

@db_retry(max_retries=3)
def create_meeting(decoded_payload=None):
    try:
        data = request.get_json()
        
        project_id = data.get("project_id")
        allocation_id = data.get("allocation_id")
        client_id = data.get("client_id")
        title = data.get("title")
        members = data.get("members")
        requirements = data.get("requirements")
        meeting_date_str = data.get("meeting_date")
        start_time_str = data.get("start_time")
        end_time_str = data.get("end_time")
        status = data.get("status", "scheduled")
        remark = data.get("remark")
        
        created_by_role_id = decoded_payload.get("role_id") if decoded_payload else None
        created_by_role = decoded_payload.get("role") if decoded_payload else None

        if not all([project_id, title, members, meeting_date_str, start_time_str]):
            return jsonify({"msg": "Project ID, Title, Members, Date, and Start Time are required", "status": 0}), 400

        try:
            meeting_date = datetime.datetime.strptime(meeting_date_str, '%Y-%m-%d').date()
            start_time = datetime.datetime.strptime(start_time_str, '%H:%M').time()
            end_time = datetime.datetime.strptime(end_time_str, '%H:%M').time() if end_time_str else None
        except ValueError:
            return jsonify({"msg": "Invalid date or time format. Use YYYY-MM-DD for date and HH:MM for time", "status": 0}), 400

        new_meeting = Meeting(
            project_id=project_id,
            allocation_id=allocation_id,
            client_id=client_id,
            title=title,
            members=members,
            requirements=requirements,
            meeting_date=meeting_date,
            start_time=start_time,
            end_time=end_time,
            status=status,
            remark=remark,
            created_by_role_id=created_by_role_id,
            created_by_role=created_by_role
        )
        db.session.add(new_meeting)
        db.session.commit()
        
        return jsonify({"msg": "Meeting scheduled successfully", "status": 1, "meeting_id": new_meeting.id}), 201
    except Exception as e:
        db.session.rollback()
        if "MySQL server has gone away" in str(e):
            return create_meeting(decoded_payload)
        else:
            return jsonify({"success": 0, "error": str(e)}), 500

@db_retry(max_retries=3)
def get_all_meetings(decoded_payload=None):
    try:
        meetings = Meeting.query.all()
        result = []
        for meeting in meetings:
            created_by_person = get_person_details(meeting.created_by_role, meeting.created_by_role_id)
            result.append({
                "id": meeting.id,
                "project_id": meeting.project_id,
                "project_name": meeting.project.name if meeting.project else None,
                "allocation_id": meeting.allocation_id,
                "client_id": meeting.client_id,
                "client_name": meeting.client.name if meeting.client else None,
                "title": meeting.title,
                "members": meeting.members,
                "requirements": meeting.requirements,
                "meeting_date": safe_isoformat(meeting.meeting_date),
                "start_time": meeting.start_time.strftime('%H:%M') if meeting.start_time else None,
                "end_time": meeting.end_time.strftime('%H:%M') if meeting.end_time else None,
                "status": meeting.status,
                "remark": meeting.remark,
                "created_by_role_id": meeting.created_by_role_id,
                "created_by_role": meeting.created_by_role,
                "created_by_person": created_by_person,
                "created_at": safe_isoformat(meeting.created_at)
            })
        return jsonify({"meetings": result, "status": 1}), 200
    except Exception as e:
        if "MySQL server has gone away" in str(e):
            return get_all_meetings(decoded_payload)
        else:
            return jsonify({"success": 0, "error": str(e)}), 500

@db_retry(max_retries=3)
def get_meeting_by_id(meeting_id, decoded_payload=None):
    try:
        meeting = Meeting.query.get(meeting_id)
        if not meeting:
            return jsonify({"message": "Meeting not found", "status": 0}), 404
        
        created_by_person = get_person_details(meeting.created_by_role, meeting.created_by_role_id)
        result = {
            "id": meeting.id,
            "project_id": meeting.project_id,
            "project_name": meeting.project.name if meeting.project else None,
            "allocation_id": meeting.allocation_id,
            "client_id": meeting.client_id,
            "client_name": meeting.client.name if meeting.client else None,
            "title": meeting.title,
            "members": meeting.members,
            "requirements": meeting.requirements,
            "meeting_date": safe_isoformat(meeting.meeting_date),
            "start_time": meeting.start_time.strftime('%H:%M') if meeting.start_time else None,
            "end_time": meeting.end_time.strftime('%H:%M') if meeting.end_time else None,
            "status": meeting.status,
            "remark": meeting.remark,
            "created_by_role_id": meeting.created_by_role_id,
            "created_by_role": meeting.created_by_role,
            "created_by_person": created_by_person,
            "created_at": safe_isoformat(meeting.created_at)
        }
        return jsonify({"meeting": result, "status": 1}), 200
    except Exception as e:
        if "MySQL server has gone away" in str(e):
            return get_meeting_by_id(meeting_id, decoded_payload)
        else:
            return jsonify({"success": 0, "error": str(e)}), 500

@db_retry(max_retries=3)
def update_meeting(meeting_id, decoded_payload=None):
    try:
        meeting = Meeting.query.get(meeting_id)
        if not meeting:
            return jsonify({"message": "Meeting not found", "status": 0}), 404
        
        data = request.get_json()
        
        meeting.project_id = data.get("project_id", meeting.project_id)
        meeting.allocation_id = data.get("allocation_id", meeting.allocation_id)
        meeting.client_id = data.get("client_id", meeting.client_id)
        meeting.title = data.get("title", meeting.title)
        meeting.members = data.get("members", meeting.members)
        meeting.requirements = data.get("requirements", meeting.requirements)
        
        meeting_date_str = data.get("meeting_date")
        if meeting_date_str:
            meeting.meeting_date = datetime.datetime.strptime(meeting_date_str, '%Y-%m-%d').date()
            
        start_time_str = data.get("start_time")
        if start_time_str:
            meeting.start_time = datetime.datetime.strptime(start_time_str, '%H:%M').time()
            
        end_time_str = data.get("end_time")
        if end_time_str:
            meeting.end_time = datetime.datetime.strptime(end_time_str, '%H:%M').time()
            
        meeting.status = data.get("status", meeting.status)
        meeting.remark = data.get("remark", meeting.remark)
        
        db.session.commit()
        return jsonify({"msg": "Meeting updated successfully", "status": 1}), 200
    except Exception as e:
        db.session.rollback()
        if "MySQL server has gone away" in str(e):
            return update_meeting(meeting_id, decoded_payload)
        else:
            return jsonify({"success": 0, "error": str(e)}), 500

@db_retry(max_retries=3)
def delete_meeting(meeting_id, decoded_payload=None):
    try:
        meeting = Meeting.query.get(meeting_id)
        if not meeting:
            return jsonify({"message": "Meeting not found", "status": 0}), 404
        
        db.session.delete(meeting)
        db.session.commit()
        return jsonify({"msg": "Meeting deleted successfully", "status": 1}), 200
    except Exception as e:
        db.session.rollback()
        if "MySQL server has gone away" in str(e):
            return delete_meeting(meeting_id, decoded_payload)
        else:
            return jsonify({"success": 0, "error": str(e)}), 500
