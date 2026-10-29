from flask import jsonify, request
import datetime
from src import db
from src.models.project_excel_model import ProjectExcel
from src.utils.role_utils import get_person_details
from src.utils.image_utils import save_file
from src.utils.db_retry import db_retry
from src.utils.date_utils import safe_isoformat

@db_retry(max_retries=3)
def create_project_excel(decoded_payload=None):
    try:
        data = request.get_json()
        
        project_id = data.get("project_id")
        file_name = data.get("file_name")
        file_data = data.get("file_data")
        role_id = data.get("role_id", 1)
        role = data.get("role", "admin")

        if not project_id or not file_name or not file_data:
            return jsonify({"msg": "Project ID, File Name and File Data are required", "status": 0}), 400

        # Save the file
        file_url = save_file(file_data, folder="project_excels")
        if not file_url:
            return jsonify({"msg": "Failed to save file", "status": 0}), 400

        new_excel = ProjectExcel(
            project_id=project_id,
            role_id=role_id,
            role=role,
            file_name=file_name,
            file_url=file_url
        )
        db.session.add(new_excel)
        db.session.commit()
        
        return jsonify({
            "msg": "Project Excel file created successfully",
            "status": 1,
            "excel_id": new_excel.id,
            "file_url": file_url,
            "file_name": file_name
        }), 201
    except Exception as e:
        db.session.rollback()
        if "MySQL server has gone away" in str(e):
            return create_project_excel(decoded_payload)
        else:
            print("Error creating excel:", str(e))
            return jsonify({"success": 0, "error": str(e)}), 500

@db_retry(max_retries=3)
def get_all_project_excels(decoded_payload=None):
    try:
        excel_files = ProjectExcel.query.all()
        result = []
        for excel in excel_files:
            result.append({
                "id": excel.id,
                "project_id": excel.project_id,
                "file_name": excel.file_name,
                "file_url": excel.file_url,
                "created_at": safe_isoformat(excel.created_at)
            })
        return jsonify({"excel_files": result, "status": 1}), 200
    except Exception as e:
        print("Error getting all excels:", str(e))
        if "MySQL server has gone away" in str(e):
            return get_all_project_excels(decoded_payload)
        else:
            return jsonify({"success": 0, "error": str(e)}), 500

@db_retry(max_retries=3)
def get_excel_by_id(excel_id, decoded_payload=None):
    try:
        excel = ProjectExcel.query.get(excel_id)
        if not excel:
            return jsonify({"message": "Excel file not found", "status": 0}), 404
        
        result = {
            "id": excel.id,
            "project_id": excel.project_id,
            "file_name": excel.file_name,
            "file_url": excel.file_url,
            "created_at": safe_isoformat(excel.created_at)
        }
        return jsonify({"excel_file": result, "status": 1}), 200
    except Exception as e:
        print("Error getting excel by id:", str(e))
        if "MySQL server has gone away" in str(e):
            return get_excel_by_id(excel_id, decoded_payload)
        else:
            return jsonify({"success": 0, "error": str(e)}), 500

@db_retry(max_retries=3)
def get_excels_by_project_id(project_id, decoded_payload=None):
    try:
        excel_files = ProjectExcel.query.filter_by(project_id=project_id).all()
        result = []
        for excel in excel_files:
            result.append({
                "id": excel.id,
                "project_id": excel.project_id,
                "file_name": excel.file_name,
                "file_url": excel.file_url,
                "created_at": safe_isoformat(excel.created_at)
            })
        return jsonify({"excel_files": result, "status": 1}), 200
    except Exception as e:
        print("Error getting excels by project id:", str(e))
        if "MySQL server has gone away" in str(e):
            return get_excels_by_project_id(project_id, decoded_payload)
        else:
            return jsonify({"success": 0, "error": str(e)}), 500

@db_retry(max_retries=3)
def update_project_excel(excel_id, decoded_payload=None):
    try:
        excel = ProjectExcel.query.get(excel_id)
        if not excel:
            return jsonify({"message": "Excel file not found", "status": 0}), 404
        
        data = request.get_json()
        
        excel.file_name = data.get("file_name", excel.file_name)
        
        db.session.commit()
        return jsonify({"msg": "Excel file updated successfully", "status": 1}), 200
    except Exception as e:
        db.session.rollback()
        if "MySQL server has gone away" in str(e):
            return update_project_excel(excel_id, decoded_payload)
        else:
            print("Error updating excel:", str(e))
            return jsonify({"success": 0, "error": str(e)}), 500

@db_retry(max_retries=3)
def delete_project_excel(excel_id, decoded_payload=None):
    try:
        excel = ProjectExcel.query.get(excel_id)
        if not excel:
            return jsonify({"message": "Excel file not found", "status": 0}), 404
        
        db.session.delete(excel)
        db.session.commit()
        return jsonify({"msg": "Excel file deleted successfully", "status": 1}), 200
    except Exception as e:
        db.session.rollback()
        if "MySQL server has gone away" in str(e):
            return delete_project_excel(excel_id, decoded_payload)
        else:
            print("Error deleting excel:", str(e))
            return jsonify({"success": 0, "error": str(e)}), 500
