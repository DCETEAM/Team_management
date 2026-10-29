from flask import jsonify, request
import datetime
from src import db
from src.models.meeting_message_model import MeetingMessage
from src.utils.role_utils import get_person_details
from src.utils.date_utils import safe_isoformat

def create_message(decoded_payload=None):
    try:
        data = request.get_json()
        
        meeting_id = data.get("meeting_id")
        message = data.get("message")
        attachment_url = data.get("attachment_url")
        attachment_name = data.get("attachment_name")
        remark = data.get("remark")
        
        role_id = decoded_payload.get("role_id") if decoded_payload else None
        role = decoded_payload.get("role") if decoded_payload else None

        if not meeting_id:
            return jsonify({"msg": "Meeting ID is required", "status": 0}), 400
        
        if not message and not attachment_url:
            return jsonify({"msg": "Message or Attachment is required", "status": 0}), 400

        new_message = MeetingMessage(
            meeting_id=meeting_id,
            role_id=role_id,
            role=role,
            message=message,
            attachment_url=attachment_url,
            attachment_name=attachment_name,
            remark=remark
        )
        db.session.add(new_message)
        db.session.commit()
        
        return jsonify({"msg": "Message sent successfully", "status": 1, "message_id": new_message.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": 0, "error": str(e)}), 500

def get_messages_by_meeting(meeting_id, decoded_payload=None):
    try:
        messages = MeetingMessage.query.filter_by(meeting_id=meeting_id).all()
        result = []
        for msg in messages:
            person = get_person_details(msg.role, msg.role_id)
            result.append({
                "id": msg.id,
                "meeting_id": msg.meeting_id,
                "role_id": msg.role_id,
                "role": msg.role,
                "person": person,
                "message": msg.message,
                "attachment_url": msg.attachment_url,
                "attachment_name": msg.attachment_name,
                "is_edited": msg.is_edited,
                "edited_at": safe_isoformat(msg.edited_at),
                "remark": msg.remark,
                "created_at": safe_isoformat(msg.created_at)
            })
        return jsonify({"messages": result, "status": 1}), 200
    except Exception as e:
        return jsonify({"success": 0, "error": str(e)}), 500

def get_message_by_id(message_id, decoded_payload=None):
    try:
        msg = MeetingMessage.query.get(message_id)
        if not msg:
            return jsonify({"message": "Message not found", "status": 0}), 404
        
        person = get_person_details(msg.role, msg.role_id)
        result = {
            "id": msg.id,
            "meeting_id": msg.meeting_id,
            "role_id": msg.role_id,
            "role": msg.role,
            "person": person,
            "message": msg.message,
            "attachment_url": msg.attachment_url,
            "attachment_name": msg.attachment_name,
            "is_edited": msg.is_edited,
            "edited_at": safe_isoformat(msg.edited_at),
            "remark": msg.remark,
            "created_at": safe_isoformat(msg.created_at)
        }
        return jsonify({"message": result, "status": 1}), 200
    except Exception as e:
        return jsonify({"success": 0, "error": str(e)}), 500

def update_message(message_id, decoded_payload=None):
    try:
        msg = MeetingMessage.query.get(message_id)
        if not msg:
            return jsonify({"message": "Message not found", "status": 0}), 404
        
        data = request.get_json()
        
        msg.message = data.get("message", msg.message)
        msg.attachment_url = data.get("attachment_url", msg.attachment_url)
        msg.attachment_name = data.get("attachment_name", msg.attachment_name)
        msg.remark = data.get("remark", msg.remark)
        msg.is_edited = True
        msg.edited_at = datetime.datetime.utcnow()
        
        db.session.commit()
        return jsonify({"msg": "Message updated successfully", "status": 1}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": 0, "error": str(e)}), 500

def delete_message(message_id, decoded_payload=None):
    try:
        msg = MeetingMessage.query.get(message_id)
        if not msg:
            return jsonify({"message": "Message not found", "status": 0}), 404

        db.session.delete(msg)
        db.session.commit()
        return jsonify({"msg": "Message deleted successfully", "status": 1}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": 0, "error": str(e)}), 500
