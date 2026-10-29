from flask import jsonify, request
import datetime
from src import db
from src.models.task_comment_model import TaskComment
from src.utils.role_utils import get_person_details

def create_comment(decoded_payload=None):
    try:
        data = request.get_json()
        
        task_id = data.get("task_id")
        comment = data.get("comment")
        remark = data.get("remark")
        
        role_id = decoded_payload.get("role_id") if decoded_payload else None
        role = decoded_payload.get("role") if decoded_payload else None

        if not task_id or not comment:
            return jsonify({"msg": "Task ID and comment are required", "status": 0}), 400

        new_comment = TaskComment(
            task_id=task_id,
            role_id=role_id,
            role=role,
            comment=comment,
            remark=remark
        )
        db.session.add(new_comment)
        db.session.commit()
        
        return jsonify({"msg": "Comment added successfully", "status": 1, "id": new_comment.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": 0, "error": str(e)}), 500

def get_comments_by_task(task_id, decoded_payload=None):
    try:
        comments = TaskComment.query.filter_by(task_id=task_id).order_by(TaskComment.created_at.desc()).all()
        result = []
        for c in comments:
            person = get_person_details(c.role, c.role_id)
            result.append({
                "id": c.id,
                "task_id": c.task_id,
                "role_id": c.role_id,
                "role": c.role,
                "person": person,
                "comment": c.comment,
                "remark": c.remark,
                "created_at": c.created_at
            })
        return jsonify({"comments": result, "status": 1}), 200
    except Exception as e:
        return jsonify({"success": 0, "error": str(e)}), 500

def get_comment_by_id(comment_id, decoded_payload=None):
    try:
        c = TaskComment.query.get(comment_id)
        if not c:
            return jsonify({"message": "Comment not found", "status": 0}), 404
        
        person = get_person_details(c.role, c.role_id)
        result = {
            "id": c.id,
            "task_id": c.task_id,
            "role_id": c.role_id,
            "role": c.role,
            "person": person,
            "comment": c.comment,
            "remark": c.remark,
            "created_at": c.created_at
        }
        return jsonify({"comment": result, "status": 1}), 200
    except Exception as e:
        return jsonify({"success": 0, "error": str(e)}), 500

def update_comment(comment_id, decoded_payload=None):
    try:
        c = TaskComment.query.get(comment_id)
        if not c:
            return jsonify({"message": "Comment not found", "status": 0}), 404

        data = request.get_json()
        
        if "comment" in data:
            c.comment = data["comment"]
        if "remark" in data:
            c.remark = data["remark"]
            
        db.session.commit()
        return jsonify({"message": "Comment updated successfully", "status": 1}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": 0, "error": str(e)}), 500

def delete_comment(comment_id, decoded_payload=None):
    try:
        c = TaskComment.query.get(comment_id)
        if not c:
            return jsonify({"message": "Comment not found", "status": 0}), 404

        db.session.delete(c)
        db.session.commit()
        return jsonify({"message": "Comment deleted successfully", "status": 1}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": 0, "error": str(e)}), 500
