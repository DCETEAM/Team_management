from flask import jsonify, request
from src import db
from src.models.client_model import Client

def create_client(decoded_payload=None):
    try:
        data = request.get_json()
        
        name = data.get("name")
        email = data.get("email")
        phone = data.get("phone")
        company = data.get("company")
        address = data.get("address")
        remark = data.get("remark")

        if not name:
            return jsonify({"msg": "Client name is required", "status": 0}), 400

        new_client = Client(
            name=name,
            email=email,
            phone=phone,
            company=company,
            address=address,
            remark=remark
        )
        db.session.add(new_client)
        db.session.commit()
        
        return jsonify({"msg": "Client created successfully", "status": 1, "client_id": new_client.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": 0, "error": str(e)}), 500

def get_all_clients(decoded_payload=None):
    try:
        clients = Client.query.all()
        result = []
        for client in clients:
            result.append({
                "id": client.id,
                "name": client.name,
                "email": client.email,
                "phone": client.phone,
                "company": client.company,
                "address": client.address,
                "remark": client.remark,
                "created_at": client.created_at
            })
        return jsonify({"clients": result, "status": 1}), 200
    except Exception as e:
        return jsonify({"success": 0, "error": str(e)}), 500

def get_client_by_id(client_id, decoded_payload=None):
    try:
        client = Client.query.get(client_id)
        if not client:
            return jsonify({"message": "Client not found", "status": 0}), 404
        
        result = {
            "id": client.id,
            "name": client.name,
            "email": client.email,
            "phone": client.phone,
            "company": client.company,
            "address": client.address,
            "remark": client.remark,
            "created_at": client.created_at
        }
        return jsonify({"client": result, "status": 1}), 200
    except Exception as e:
        return jsonify({"success": 0, "error": str(e)}), 500

def update_client(client_id, decoded_payload=None):
    try:
        client = Client.query.get(client_id)
        if not client:
            return jsonify({"message": "Client not found", "status": 0}), 404

        data = request.get_json()
        
        if "name" in data:
            client.name = data["name"]
        if "email" in data:
            client.email = data["email"]
        if "phone" in data:
            client.phone = data["phone"]
        if "company" in data:
            client.company = data["company"]
        if "address" in data:
            client.address = data["address"]
        if "remark" in data:
            client.remark = data["remark"]
            
        db.session.commit()
        return jsonify({"message": "Client updated successfully", "status": 1}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": 0, "error": str(e)}), 500

def delete_client(client_id, decoded_payload=None):
    try:
        client = Client.query.get(client_id)
        if not client:
            return jsonify({"message": "Client not found", "status": 0}), 404
            
        db.session.delete(client)
        db.session.commit()
        return jsonify({"message": "Client deleted successfully", "status": 1}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": 0, "error": str(e)}), 500
