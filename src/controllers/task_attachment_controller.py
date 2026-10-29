from flask import jsonify, request, send_from_directory
import datetime
import os
from uuid import uuid4
from werkzeug.utils import safe_join
from src import db
from src.models.task_attachment_model import TaskAttachment
from src.utils.role_utils import get_person_details
from src.utils.image_utils import save_attachment, delete_image
from src.utils.date_utils import safe_isoformat

# Define the upload folder
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, '..', 'assets', 'attachments')
UPLOAD_FOLDER = os.path.normpath(UPLOAD_FOLDER)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Maximum file size: 10MB
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB in bytes

def create_attachment(decoded_payload=None):
    try:
        file_url = None
        file_name = None
        file_size = None
        remark = None
        
        # Check if it's a multipart/form-data request (file upload)
        if request.files and 'file' in request.files:
            file = request.files['file']
            if file.filename == '':
                return jsonify({"msg": "No selected file", "status": 0}), 400
            
            task_id = request.form.get("task_id")
            remark = request.form.get("remark")
            
            if not task_id:
                return jsonify({"msg": "Task ID is required", "status": 0}), 400
            
            # Check file size
            file.seek(0, os.SEEK_END)
            file_size = file.tell()
            file.seek(0)
            
            if file_size > MAX_FILE_SIZE:
                return jsonify({"msg": "File size exceeds 10MB limit", "status": 0}), 400
            
            # Generate a unique filename to avoid conflicts
            original_filename = file.filename
            file_ext = os.path.splitext(original_filename)[1]
            unique_filename = f"{uuid4().hex}{file_ext}"
            filepath = os.path.join(UPLOAD_FOLDER, unique_filename)
            
            # Save the file
            file.save(filepath)
            
            file_url = f"/src/assets/attachments/{unique_filename}"
            file_name = original_filename
        
        # Else, check if it's a JSON request with base64 data
        else:
            data = request.get_json() or {}
            task_id = data.get("task_id")
            file_data = data.get("file_data")
            file_name = data.get("file_name")
            file_size = data.get("file_size")
            remark = data.get("remark")
            
            if not task_id:
                return jsonify({"msg": "Task ID is required", "status": 0}), 400
            
            if file_data:
                # Use save_attachment from image_utils.py for base64 files
                file_url = save_attachment(file_data, file_name)
                if not file_url:
                    return jsonify({"msg": "Failed to save attachment", "status": 0}), 400
        
        if not file_url:
            return jsonify({"msg": "No file data provided", "status": 0}), 400
        
        role_id = decoded_payload.get("role_id") if decoded_payload else None
        role = decoded_payload.get("role") if decoded_payload else None
        
        new_attachment = TaskAttachment(
            task_id=int(task_id),
            role_id=role_id,
            role=role,
            file_name=file_name,
            file_url=file_url,
            file_size=file_size,
            remark=remark
        )
        db.session.add(new_attachment)
        db.session.commit()
        
        return jsonify({"msg": "Attachment created successfully", "status": 1, "attachment_id": new_attachment.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": 0, "error": str(e)}), 500

def get_all_attachments(decoded_payload=None):
    try:
        attachments = TaskAttachment.query.all()
        result = []
        for attachment in attachments:
            person = get_person_details(attachment.role, attachment.role_id)
            result.append({
                "id": attachment.id,
                "task_id": attachment.task_id,
                "task_title": attachment.task.title if attachment.task else None,
                "role_id": attachment.role_id,
                "role": attachment.role,
                "person": person,
                "file_name": attachment.file_name,
                "file_url": attachment.file_url,
                "file_size": attachment.file_size,
                "remark": attachment.remark,
                "created_at": safe_isoformat(attachment.created_at),
                "updated_at": safe_isoformat(attachment.updated_at)
            })
        return jsonify({"attachments": result, "status": 1}), 200
    except Exception as e:
        return jsonify({"success": 0, "error": str(e)}), 500

def get_attachments_by_task_id(task_id, decoded_payload=None):
    try:
        attachments = TaskAttachment.query.filter_by(task_id=task_id).all()
        result = []
        for attachment in attachments:
            person = get_person_details(attachment.role, attachment.role_id)
            result.append({
                "id": attachment.id,
                "task_id": attachment.task_id,
                "task_title": attachment.task.title if attachment.task else None,
                "role_id": attachment.role_id,
                "role": attachment.role,
                "person": person,
                "file_name": attachment.file_name,
                "file_url": attachment.file_url,
                "file_size": attachment.file_size,
                "remark": attachment.remark,
                "created_at": safe_isoformat(attachment.created_at),
                "updated_at": safe_isoformat(attachment.updated_at)
            })
        return jsonify({"attachments": result, "status": 1}), 200
    except Exception as e:
        return jsonify({"success": 0, "error": str(e)}), 500

def get_attachment_by_id(attachment_id, decoded_payload=None):
    try:
        attachment = TaskAttachment.query.get(attachment_id)
        if not attachment:
            return jsonify({"message": "Attachment not found", "status": 0}), 404
        
        person = get_person_details(attachment.role, attachment.role_id)
        result = {
            "id": attachment.id,
            "task_id": attachment.task_id,
            "task_title": attachment.task.title if attachment.task else None,
            "role_id": attachment.role_id,
            "role": attachment.role,
            "person": person,
            "file_name": attachment.file_name,
            "file_url": attachment.file_url,
            "file_size": attachment.file_size,
            "remark": attachment.remark,
            "created_at": safe_isoformat(attachment.created_at),
            "updated_at": safe_isoformat(attachment.updated_at)
        }
        return jsonify({"attachment": result, "status": 1}), 200
    except Exception as e:
        return jsonify({"success": 0, "error": str(e)}), 500

def download_file(filename, decoded_payload=None):
    try:
        # Check if filename is a URL path (like /src/assets/attachments/...)
        if filename.startswith("/src/assets/"):
            # Extract the actual filename
            filename = filename.split("/")[-1]
        
        # Check if the file exists in our upload folder
        file_path = safe_join(UPLOAD_FOLDER, filename)
        if os.path.exists(file_path):
            return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)
        
        # Else, try the static assets folder (from config.SERVE_STATIC_FOLDER)
        from src import create_app
        app = create_app()
        with app.app_context():
            base_path = app.config["SERVE_STATIC_FOLDER"]
            static_file_path = safe_join(base_path, "attachments", filename)
            if os.path.exists(static_file_path):
                return send_from_directory(safe_join(base_path, "attachments"), filename, as_attachment=True)
        
        return jsonify({"msg": "File not found", "status": 0}), 404
    except Exception as e:
        return jsonify({"success": 0, "error": str(e)}), 500

def update_attachment(attachment_id, decoded_payload=None):
    try:
        attachment = TaskAttachment.query.get(attachment_id)
        if not attachment:
            return jsonify({"message": "Attachment not found", "status": 0}), 404
        
        data = request.get_json()
        
        attachment.file_name = data.get("file_name", attachment.file_name)
        attachment.remark = data.get("remark", attachment.remark)
        
        db.session.commit()
        return jsonify({"msg": "Attachment updated successfully", "status": 1}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": 0, "error": str(e)}), 500

def delete_attachment(attachment_id, decoded_payload=None):
    try:
        attachment = TaskAttachment.query.get(attachment_id)
        if not attachment:
            return jsonify({"message": "Attachment not found", "status": 0}), 404
        
        # Delete the physical file using delete_image utility
        delete_image(attachment.file_url)
        
        db.session.delete(attachment)
        db.session.commit()
        return jsonify({"msg": "Attachment deleted successfully", "status": 1}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": 0, "error": str(e)}), 500