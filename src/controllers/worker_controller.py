from flask import jsonify, request
import bcrypt
from src import db
from src.models.worker_model import Worker
from src.models.user_model import User
from src.utils.date_utils import parse_date
from src.utils.image_utils import save_image, delete_image
from src.utils.avatar_utils import apply_avatar_update
from src.utils.db_retry import db_retry

@db_retry(max_retries=3)
def create_worker(decoded_payload=None):
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
        
        is_tl = data.get("is_tl", False)
        is_worker = data.get("is_worker", False)
        remark = data.get("remark")
        remark = remark.strip() if remark else None

        job_title = data.get("job_title")
        job_title = job_title.strip() if job_title else None
        department = data.get("department")
        department = department.strip() if department else None
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
        github_url = data.get("github_url")
        github_url = github_url.strip() if github_url else None
        linkedin_url = data.get("linkedin_url")
        linkedin_url = linkedin_url.strip() if linkedin_url else None
        portfolio_url = data.get("portfolio_url")
        portfolio_url = portfolio_url.strip() if portfolio_url else None
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
        joining_date = parse_date(data.get("joining_date"))
        employment_type = data.get("employment_type")
        employment_type = employment_type.strip() if employment_type else None
        status = data.get("status", "ACTIVE")

        if not all([email, first_name, last_name]):
            return jsonify({"msg": "Missing required fields", "status": 0}), 400

        if User.query.filter_by(email=email).first():
            return jsonify({"msg": "User with this email already exists", "status": 0}), 409

        # Determine role based on boolean values
        role = "worker" # default
        if is_tl:
            role = "team_leader"
        elif is_worker:
            role = "worker"

        hashed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

        # 1. Create Worker
        new_worker = Worker(
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            email=email,
            avatar_url=final_avatar_url,
            is_tl=is_tl,
            is_worker=is_worker,
            job_title=job_title,
            department=department,
            experience_years=experience_years,
            working_hours=working_hours,
            work_mode=work_mode,
            office_location=office_location,
            github_url=github_url,
            linkedin_url=linkedin_url,
            portfolio_url=portfolio_url,
            address_line1=address_line1,
            address_line2=address_line2,
            city=city,
            state=state,
            country=country,
            pincode=pincode,
            joining_date=joining_date,
            employment_type=employment_type,
            status=status,
            remark=remark
        )
        db.session.add(new_worker)
        db.session.flush()

        # 2. Create User
        new_user = User(
            email=email, password=hashed_password.decode("utf-8"), role=role, role_id=new_worker.id
        )
        db.session.add(new_user)
        
        db.session.commit()
        return jsonify({"msg": "Worker created successfully", "status": 1}), 201
    except Exception as e:
        db.session.rollback()
        if "MySQL server has gone away" in str(e):
            return create_worker(decoded_payload)
        else:
            return jsonify({"success": 0, "error": str(e)}), 500

@db_retry(max_retries=3)
def get_all_workers(decoded_payload=None):
    try:
        workers = Worker.query.all()
        result = []
        for worker in workers:
            user = User.query.filter_by(role_id=worker.id).filter(User.role.in_(['team_leader', 'worker'])).first()
            result.append({
                "id": worker.id,
                "first_name": worker.first_name,
                "last_name": worker.last_name,
                "phone": worker.phone,
                "email": worker.email,
                "avatar_url": worker.avatar_url,
                "is_tl": worker.is_tl,
                "is_worker": worker.is_worker,
                "job_title": worker.job_title,
                "department": worker.department,
                "experience_years": worker.experience_years,
                "working_hours": worker.working_hours,
                "work_mode": worker.work_mode,
                "office_location": worker.office_location,
                "github_url": worker.github_url,
                "linkedin_url": worker.linkedin_url,
                "portfolio_url": worker.portfolio_url,
                "address_line1": worker.address_line1,
                "address_line2": worker.address_line2,
                "city": worker.city,
                "state": worker.state,
                "country": worker.country,
                "pincode": worker.pincode,
                "joining_date": worker.joining_date,
                "employment_type": worker.employment_type,
                "status": worker.status,
                "remark": worker.remark,
                "user_email": user.email if user else None,
                "is_active": user.is_active if user else None
            })
        return jsonify({"workers": result, "status": 1}), 200
    except Exception as e:
        if "MySQL server has gone away" in str(e):
            return get_all_workers(decoded_payload)
        else:
            return jsonify({"success": 0, "error": str(e)}), 500

@db_retry(max_retries=3)
def get_worker_by_id(worker_id, decoded_payload=None):
    try:
        worker = Worker.query.get(worker_id)
        if not worker:
            return jsonify({"message": "Worker not found", "status": 0}), 404
        
        user = User.query.filter_by(role_id=worker.id).filter(User.role.in_(['team_leader', 'worker'])).first()
        result = {
            "id": worker.id,
            "first_name": worker.first_name,
            "last_name": worker.last_name,
            "phone": worker.phone,
            "email": worker.email,
            "avatar_url": worker.avatar_url,
            "is_tl": worker.is_tl,
            "is_worker": worker.is_worker,
            "job_title": worker.job_title,
            "department": worker.department,
            "experience_years": worker.experience_years,
            "working_hours": worker.working_hours,
            "work_mode": worker.work_mode,
            "office_location": worker.office_location,
            "github_url": worker.github_url,
            "linkedin_url": worker.linkedin_url,
            "portfolio_url": worker.portfolio_url,
            "address_line1": worker.address_line1,
            "address_line2": worker.address_line2,
            "city": worker.city,
            "state": worker.state,
            "country": worker.country,
            "pincode": worker.pincode,
            "joining_date": worker.joining_date,
            "employment_type": worker.employment_type,
            "status": worker.status,
            "remark": worker.remark,
            "user_email": user.email if user else None,
            "is_active": user.is_active if user else None
        }
        return jsonify({"worker": result, "status": 1}), 200
    except Exception as e:
        if "MySQL server has gone away" in str(e):
            return get_worker_by_id(worker_id, decoded_payload)
        else:
            return jsonify({"success": 0, "error": str(e)}), 500

@db_retry(max_retries=3)
def update_worker(worker_id, decoded_payload=None):
    try:
        worker = Worker.query.get(worker_id)
        if not worker:
            return jsonify({"message": "Worker not found", "status": 0}), 404

        user = User.query.filter_by(role_id=worker.id).filter(User.role.in_(['team_leader', 'worker'])).first()
        data = request.get_json()
        
        if "first_name" in data:
            worker.first_name = data["first_name"]
        if "last_name" in data:
            worker.last_name = data["last_name"]
        if "phone" in data:
            worker.phone = data["phone"].strip() if data["phone"] else None
        if "email" in data:
            new_email = data["email"]
            # Check if email is already taken by another user
            existing_user = User.query.filter_by(email=new_email).first()
            if existing_user and existing_user.id != user.id:
                return jsonify({"msg": f"User with email '{new_email}' already exists", "status": 0}), 409
            worker.email = new_email
            if user:
                user.email = new_email
        if "avatar_url" in data:
            apply_avatar_update(worker, data["avatar_url"])
        if "is_tl" in data:
            worker.is_tl = data["is_tl"]
        if "is_worker" in data:
            worker.is_worker = data["is_worker"]
        if "job_title" in data:
            worker.job_title = data["job_title"].strip() if data["job_title"] else None
        if "department" in data:
            worker.department = data["department"].strip() if data["department"] else None
        if "experience_years" in data:
            exp_val = data["experience_years"]
            if exp_val == "" or exp_val is None:
                worker.experience_years = None
            else:
                try:
                    worker.experience_years = float(exp_val)
                except (ValueError, TypeError):
                    worker.experience_years = None
        if "working_hours" in data:
            wh_val = data["working_hours"]
            if wh_val == "" or wh_val is None:
                worker.working_hours = None
            else:
                try:
                    worker.working_hours = int(wh_val)
                except (ValueError, TypeError):
                    worker.working_hours = None
        if "work_mode" in data:
            worker.work_mode = data["work_mode"].strip() if data["work_mode"] else None
        if "office_location" in data:
            worker.office_location = data["office_location"].strip() if data["office_location"] else None
        if "github_url" in data:
            worker.github_url = data["github_url"].strip() if data["github_url"] else None
        if "linkedin_url" in data:
            worker.linkedin_url = data["linkedin_url"].strip() if data["linkedin_url"] else None
        if "portfolio_url" in data:
            worker.portfolio_url = data["portfolio_url"].strip() if data["portfolio_url"] else None
        if "address_line1" in data:
            worker.address_line1 = data["address_line1"].strip() if data["address_line1"] else None
        if "address_line2" in data:
            worker.address_line2 = data["address_line2"].strip() if data["address_line2"] else None
        if "city" in data:
            worker.city = data["city"].strip() if data["city"] else None
        if "state" in data:
            worker.state = data["state"].strip() if data["state"] else None
        if "country" in data:
            worker.country = data["country"].strip() if data["country"] else None
        if "pincode" in data:
            worker.pincode = data["pincode"].strip() if data["pincode"] else None
        if "joining_date" in data:
            worker.joining_date = parse_date(data["joining_date"])
        if "employment_type" in data:
            worker.employment_type = data["employment_type"].strip() if data["employment_type"] else None
        if "status" in data:
            worker.status = data["status"]
        if "remark" in data:
            worker.remark = data["remark"].strip() if data["remark"] else None
            
        if "is_active" in data and user:
            user.is_active = data["is_active"]

        # Sync User role if it has changed based on booleans
        if user:
            if worker.is_tl:
                user.role = "team_leader"
            elif worker.is_worker:
                user.role = "worker"

        db.session.commit()
        return jsonify({"message": "Worker updated successfully", "status": 1}), 200
    except Exception as e:
        db.session.rollback()
        if "MySQL server has gone away" in str(e):
            return update_worker(worker_id, decoded_payload)
        else:
            # Check for duplicate entry error
            if "Duplicate entry" in str(e):
                if "email" in str(e):
                    return jsonify({"msg": "Email already exists", "status": 0}), 409
            return jsonify({"success": 0, "error": str(e)}), 500

@db_retry(max_retries=3)
def delete_worker(worker_id, decoded_payload=None):
    try:
        worker = Worker.query.get(worker_id)
        if not worker:
            return jsonify({"message": "Worker not found", "status": 0}), 404
        
        # Check if worker is in any project allocation (with worker/team_leader role)
        from src.models.project_allocation_model import ProjectAllocation
        allocations = ProjectAllocation.query.all()
        in_allocation = False
        for alloc in allocations:
            if alloc.members:
                for member in alloc.members:
                    if member.get("user_id") == worker_id and member.get("role") in ["worker", "team_leader"]:
                        in_allocation = True
                        break
            if in_allocation:
                break
        
        # Check if worker is in any task (with worker role only for task table)
        from src.models.task_model import Task
        tasks = Task.query.all()
        in_task = False
        for task in tasks:
            task_members = task.worker_ids if task.worker_ids else task.members
            if task_members:
                for member in task_members:
                    member_role = member.get("role") or member.get("type")
                    if member.get("user_id") == worker_id and member_role == "worker":
                        in_task = True
                        break
            if in_task:
                break
        
        if in_allocation or in_task:
            return jsonify({
                "msg": "Cannot delete this worker because they are allocated to projects or assigned to tasks", 
                "status": 0
            }), 400
            
        user = User.query.filter_by(role_id=worker.id).filter(User.role.in_(['team_leader', 'worker'])).first()
        if user:
            db.session.delete(user)
            
        # Delete avatar image if exists
        delete_image(worker.avatar_url)
        
        db.session.delete(worker)
        db.session.commit()
        return jsonify({"message": "Worker deleted successfully", "status": 1}), 200
    except Exception as e:
        db.session.rollback()
        if "MySQL server has gone away" in str(e):
            return delete_worker(worker_id, decoded_payload)
        else:
            return jsonify({"success": 0, "error": str(e)}), 500
