import bcrypt
import datetime
from flask import jsonify, request, current_app
from src import db
from src.models.admin_model import Admin
from src.models.user_model import User
from src.utils.date_utils import parse_date
from src.utils.image_utils import save_image, delete_image
from src.utils.avatar_utils import apply_avatar_update
from src.utils.db_retry import db_retry

@db_retry(max_retries=3)
def create_admin(decoded_payload=None):
    try:
        data = request.get_json()
        
        email = data.get("email")
        password = "Dce@2026"
        first_name = data.get("first_name")
        last_name = data.get("last_name")
        phone = data.get("phone")
        phone = phone.strip() if phone else None
        avatar_url = data.get("avatar_url")
        
        # Save image if provided as base64
        saved_url = save_image(avatar_url)
        final_avatar_url = saved_url if saved_url else avatar_url
        
        is_superadmin = data.get("is_superadmin", False)
        is_admin = data.get("is_admin", False)
        is_scrum = data.get("is_scrum", False)
        remark = data.get("remark")
        remark = remark.strip() if remark else None

        experience_years = data.get("experience_years")
        if experience_years == "" or experience_years is None:
            experience_years = None
        else:
            try:
                experience_years = float(experience_years)
            except (ValueError, TypeError):
                experience_years = None
        working_hours = data.get("working_hours")
        if working_hours == "" or working_hours is None:
            working_hours = None
        else:
            try:
                working_hours = int(working_hours)
            except (ValueError, TypeError):
                working_hours = None
        work_mode = data.get("work_mode")
        work_mode = work_mode.strip() if work_mode else None
        office_location = data.get("office_location")
        office_location = office_location.strip() if office_location else None
        linkedin_url = data.get("linkedin_url")
        linkedin_url = linkedin_url.strip() if linkedin_url else None
        address_line1 = data.get("address_line1")
        address_line1 = address_line1.strip() if address_line1 else None
        address_line2 = data.get("address_line2")
        address_line2 = address_line2.strip() if address_line2 else None
        city = data.get("city")
        city = city.strip() if city else None
        state = data.get("state")
        state = state.strip() if state else None
        country = data.get("country")
        country = country.strip() if country else None
        pincode = data.get("pincode")
        pincode = pincode.strip() if pincode else None
        status = data.get("status", "ACTIVE")
        joining_date = parse_date(data.get("joining_date"))

        if not all([email, first_name, last_name]):
            return jsonify({"msg": "First name, last name and email are mandatory", "status": 0}), 400

        if User.query.filter_by(email=email).first():
            return jsonify({"msg": "User with this email already exists", "status": 0}), 409

        # Determine role based on boolean values
        role = "admin" # default
        if is_superadmin:
            role = "superadmin"
        elif is_admin:
            role = "admin"
        elif is_scrum:
            role = "scrum"

        hashed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

        # 1. Create Admin
        new_admin = Admin(
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            email=email,
            avatar_url=final_avatar_url,
            is_superadmin=is_superadmin,
            is_admin=is_admin,
            is_scrum=is_scrum,
            experience_years=experience_years,
            working_hours=working_hours,
            work_mode=work_mode,
            office_location=office_location,
            linkedin_url=linkedin_url,
            address_line1=address_line1,
            address_line2=address_line2,
            city=city,
            state=state,
            country=country,
            pincode=pincode,
            status=status,
            joining_date=joining_date,
            remark=remark
        )
        db.session.add(new_admin)
        db.session.flush()

        # 2. Create User
        new_user = User(
            email=email, password=hashed_password.decode("utf-8"), role=role, role_id=new_admin.id
        )
        db.session.add(new_user)
        
        db.session.commit()
        return jsonify({"msg": "Admin created successfully", "status": 1}), 201
    except Exception as e:
        db.session.rollback()
        if "MySQL server has gone away" in str(e):
            return create_admin(decoded_payload)
        else:
            return jsonify({"success": 0, "error": str(e)}), 500

@db_retry(max_retries=3)
def get_all_admins(decoded_payload=None):
    try:
        admins = Admin.query.all()
        result = []
        for admin in admins:
            user = User.query.filter_by(role_id=admin.id).filter(User.role.in_(['superadmin', 'admin', 'scrum'])).first()
            result.append({
                "id": admin.id,
                "first_name": admin.first_name,
                "last_name": admin.last_name,
                "phone": admin.phone,
                "email": admin.email,
                "avatar_url": admin.avatar_url,
                "is_superadmin": admin.is_superadmin,
                "is_admin": admin.is_admin,
                "is_scrum": admin.is_scrum,
                "experience_years": admin.experience_years,
                "working_hours": admin.working_hours,
                "work_mode": admin.work_mode,
                "office_location": admin.office_location,
                "linkedin_url": admin.linkedin_url,
                "address_line1": admin.address_line1,
                "address_line2": admin.address_line2,
                "city": admin.city,
                "state": admin.state,
                "country": admin.country,
                "pincode": admin.pincode,
                "status": admin.status,
                "last_login": admin.last_login,
                "joining_date": admin.joining_date,
                "remark": admin.remark,
                "user_email": user.email if user else None,
                "is_active": user.is_active if user else None
            })
        return jsonify({"admins": result, "status": 1}), 200
    except Exception as e:
        if "MySQL server has gone away" in str(e):
            return get_all_admins(decoded_payload)
        else:
            return jsonify({"success": 0, "error": str(e)}), 500

@db_retry(max_retries=3)
def get_admin_by_id(admin_id, decoded_payload=None):
    try:
        admin = db.session.get(Admin, admin_id)
        if not admin:
            return jsonify({"message": "Admin not found", "status": 0}), 404
        
        user = User.query.filter_by(role_id=admin.id).filter(User.role.in_(['superadmin', 'admin', 'scrum'])).first()
        result = {
            "id": admin.id,
            "first_name": admin.first_name,
            "last_name": admin.last_name,
            "phone": admin.phone,
            "email": admin.email,
            "avatar_url": admin.avatar_url,
            "is_superadmin": admin.is_superadmin,
            "is_admin": admin.is_admin,
            "is_scrum": admin.is_scrum,
            "experience_years": admin.experience_years,
            "working_hours": admin.working_hours,
            "work_mode": admin.work_mode,
            "office_location": admin.office_location,
            "linkedin_url": admin.linkedin_url,
            "address_line1": admin.address_line1,
            "address_line2": admin.address_line2,
            "city": admin.city,
            "state": admin.state,
            "country": admin.country,
            "pincode": admin.pincode,
            "status": admin.status,
            "last_login": admin.last_login,
            "joining_date": admin.joining_date,
            "remark": admin.remark,
            "user_email": user.email if user else None,
            "is_active": user.is_active if user else None
        }
        return jsonify({"admin": result, "status": 1}), 200
    except Exception as e:
        if "MySQL server has gone away" in str(e):
            return get_admin_by_id(admin_id, decoded_payload)
        else:
            return jsonify({"success": 0, "error": str(e)}), 500

@db_retry(max_retries=3)
def update_admin(admin_id, decoded_payload=None):
    try:
        admin = db.session.get(Admin, admin_id)
        if not admin:
            return jsonify({"message": "Admin not found", "status": 0}), 404

        user = User.query.filter_by(role_id=admin.id).filter(User.role.in_(['superadmin', 'admin', 'scrum'])).first()
        data = request.get_json()
        
        if "avatar_url" in data:
            apply_avatar_update(admin, data["avatar_url"])
            
        if "first_name" in data:
            admin.first_name = data["first_name"]
        if "last_name" in data:
            admin.last_name = data["last_name"]
        if "email" in data:
            new_email = data["email"]
            # Check if email is already taken by another user
            existing_user = User.query.filter_by(email=new_email).first()
            if existing_user and existing_user.id != user.id:
                return jsonify({"msg": f"User with email '{new_email}' already exists", "status": 0}), 409
            admin.email = new_email
            if user:
                user.email = new_email
        if "phone" in data:
            admin.phone = data["phone"].strip() if data["phone"] else None
        if "is_superadmin" in data:
            admin.is_superadmin = data["is_superadmin"]
        if "is_admin" in data:
            admin.is_admin = data["is_admin"]
        if "is_scrum" in data:
            admin.is_scrum = data["is_scrum"]
        if "experience_years" in data:
            exp_val = data["experience_years"]
            if exp_val == "" or exp_val is None:
                admin.experience_years = None
            else:
                try:
                    admin.experience_years = float(exp_val)
                except (ValueError, TypeError):
                    admin.experience_years = None
        if "working_hours" in data:
            wh_val = data["working_hours"]
            if wh_val == "" or wh_val is None:
                admin.working_hours = None
            else:
                try:
                    admin.working_hours = int(wh_val)
                except (ValueError, TypeError):
                    admin.working_hours = None
        if "work_mode" in data:
            admin.work_mode = data["work_mode"].strip() if data["work_mode"] else None
        if "office_location" in data:
            admin.office_location = data["office_location"].strip() if data["office_location"] else None
        if "linkedin_url" in data:
            admin.linkedin_url = data["linkedin_url"].strip() if data["linkedin_url"] else None
        if "address_line1" in data:
            admin.address_line1 = data["address_line1"].strip() if data["address_line1"] else None
        if "address_line2" in data:
            admin.address_line2 = data["address_line2"].strip() if data["address_line2"] else None
        if "city" in data:
            admin.city = data["city"].strip() if data["city"] else None
        if "state" in data:
            admin.state = data["state"].strip() if data["state"] else None
        if "country" in data:
            admin.country = data["country"].strip() if data["country"] else None
        if "pincode" in data:
            admin.pincode = data["pincode"].strip() if data["pincode"] else None
        if "status" in data:
            admin.status = data["status"]
        if "joining_date" in data:
            admin.joining_date = parse_date(data["joining_date"])
        if "remark" in data:
            admin.remark = data["remark"].strip() if data["remark"] else None
            
        if "is_active" in data and user:
            user.is_active = data["is_active"]

        # Sync User role if it has changed based on booleans
        if user:
            if admin.is_superadmin:
                user.role = "superadmin"
            elif admin.is_admin:
                user.role = "admin"
            elif admin.is_scrum:
                user.role = "scrum"

        db.session.commit()
        return jsonify({"message": "Admin updated successfully", "status": 1}), 200
    except Exception as e:
        db.session.rollback()
        if "MySQL server has gone away" in str(e):
            return update_admin(admin_id, decoded_payload)
        else:
            # Check for duplicate entry error
            if "Duplicate entry" in str(e):
                if "email" in str(e):
                    return jsonify({"msg": "Email already exists", "status": 0}), 409
            return jsonify({"success": 0, "error": str(e)}), 500

@db_retry(max_retries=3)
def delete_admin(admin_id, decoded_payload=None):
    try:
        admin = Admin.query.get(admin_id)
        if not admin:
            return jsonify({"message": "Admin not found", "status": 0}), 404
        
        # Check if admin is in any project allocation (with admin roles)
        from src.models.project_allocation_model import ProjectAllocation
        allocations = ProjectAllocation.query.all()
        in_allocation = False
        for alloc in allocations:
            if alloc.members:
                for member in alloc.members:
                    member_role = member.get("role") or member.get("type")
                    if member.get("user_id") == admin_id and member_role in ["admin", "superadmin", "scrum"]:
                        in_allocation = True
                        break
            if in_allocation:
                break
        
        # Check if admin is in any task (with admin role only for task table)
        from src.models.task_model import Task
        tasks = Task.query.all()
        in_task = False
        for task in tasks:
            task_members = task.worker_ids if task.worker_ids else task.members
            if task_members:
                for member in task_members:
                    member_role = member.get("role") or member.get("type")
                    if member.get("user_id") == admin_id and member_role == "admin":
                        in_task = True
                        break
            if in_task:
                break
        
        if in_allocation or in_task:
            return jsonify({
                "msg": "Cannot delete this admin because they are allocated to projects or assigned to tasks", 
                "status": 0
            }), 400
            
        user = User.query.filter_by(role_id=admin.id).filter(User.role.in_(['superadmin', 'admin', 'scrum'])).first()
        if user:
            db.session.delete(user)
            
        # Delete avatar image if exists
        delete_image(admin.avatar_url)
        
        db.session.delete(admin)
        db.session.commit()
        return jsonify({"message": "Admin deleted successfully", "status": 1}), 200
    except Exception as e:
        db.session.rollback()
        if "MySQL server has gone away" in str(e):
            return delete_admin(admin_id, decoded_payload)
        else:
            return jsonify({"success": 0, "error": str(e)}), 500
