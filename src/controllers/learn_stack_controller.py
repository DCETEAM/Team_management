import os
import uuid
from flask import current_app, jsonify, request

from src import db
from src.models.learn_stack_model import (
    LearnStackCard,
    LearnStackComment,
    LearnStackDomain,
    LearnStackLike,
    LearnStackStep,
    LearnStackTechnology,
    LearnStackView,
)
from src.utils.image_utils import delete_image, save_attachment, save_image
from src.utils.project_permissions import is_admin_role
from src.utils.role_utils import get_person_details


def _jwt_role_id(decoded_payload):
    return decoded_payload.get("role_id") or decoded_payload.get("roleId")


def _jwt_role(decoded_payload):
    return (decoded_payload.get("role") or "").strip().lower()


def _admin_only(decoded_payload):
    return is_admin_role(_jwt_role(decoded_payload))


def _domain_dict(d):
    return {
        "id": d.id,
        "name": d.name,
        "description": d.description,
        "color": d.color,
        "sort_order": d.sort_order,
        "is_active": d.is_active,
        "created_at": d.created_at.isoformat() if d.created_at else None,
    }


def _technology_dict(t):
    return {
        "id": t.id,
        "domain_id": t.domain_id,
        "domain_name": t.domain.name if t.domain else None,
        "name": t.name,
        "description": t.description,
        "sort_order": t.sort_order,
        "is_active": t.is_active,
        "created_at": t.created_at.isoformat() if t.created_at else None,
    }


def _step_dict(s):
    return {
        "id": s.id,
        "step_order": s.step_order,
        "title": s.title,
        "body": s.body,
        "image_url": s.image_url,
        "document_url": s.document_url,
    }


def _card_author(card):
    return get_person_details(card.created_by_role, card.created_by_role_id)


def _card_summary(card, decoded_payload=None):
    role_id = _jwt_role_id(decoded_payload) if decoded_payload else None
    role = _jwt_role(decoded_payload) if decoded_payload else None
    liked = False
    if role_id is not None and role:
        liked = (
            LearnStackLike.query.filter_by(
                card_id=card.id, role_id=role_id, role=role
            ).first()
            is not None
        )
    return {
        "id": card.id,
        "domain_id": card.domain_id,
        "domain_name": card.domain.name if card.domain else None,
        "technology_id": card.technology_id,
        "technology_name": card.technology.name if card.technology else None,
        "title": card.title,
        "description": card.description,
        "overview_document_url": card.overview_document_url,
        "is_published": card.is_published,
        "author": _card_author(card),
        "like_count": card.likes.count(),
        "comment_count": card.comments.count(),
        "view_count": card.views.count(),
        "liked_by_me": liked,
        "created_at": card.created_at.isoformat() if card.created_at else None,
        "updated_at": card.updated_at.isoformat() if card.updated_at else None,
    }


def _card_detail(card, decoded_payload=None):
    data = _card_summary(card, decoded_payload)
    data["steps"] = [_step_dict(s) for s in card.steps.order_by(LearnStackStep.step_order.asc())]
    readers = []
    for v in card.views.order_by(LearnStackView.last_viewed_at.desc()).limit(50):
        person = get_person_details(v.role, v.role_id)
        if person:
            readers.append(
                {
                    **person,
                    "first_viewed_at": v.first_viewed_at.isoformat() if v.first_viewed_at else None,
                    "last_viewed_at": v.last_viewed_at.isoformat() if v.last_viewed_at else None,
                }
            )
    data["readers"] = readers
    return data


def _can_edit_card(card, decoded_payload):
    if _admin_only(decoded_payload):
        return True
    return (
        card.created_by_role_id == _jwt_role_id(decoded_payload)
        and card.created_by_role == _jwt_role(decoded_payload)
    )


# --- Domains (admin CRUD) ---


def list_domains(decoded_payload=None):
    try:
        q = LearnStackDomain.query.order_by(
            LearnStackDomain.sort_order.asc(), LearnStackDomain.name.asc()
        )
        active_only = request.args.get("active_only", "1") == "1"
        if active_only and not _admin_only(decoded_payload):
            q = q.filter_by(is_active=True)
        rows = [_domain_dict(d) for d in q.all()]
        return jsonify({"domains": rows, "status": 1}), 200
    except Exception as e:
        return jsonify({"msg": str(e), "status": 0}), 500


def create_domain(decoded_payload=None):
    if not _admin_only(decoded_payload):
        return jsonify({"msg": "Admin only", "status": 0}), 403
    try:
        data = request.get_json() or {}
        name = (data.get("name") or "").strip()
        if not name:
            return jsonify({"msg": "Name is required", "status": 0}), 400
        if LearnStackDomain.query.filter_by(name=name).first():
            return jsonify({"msg": "Domain already exists", "status": 0}), 409
        last = LearnStackDomain.query.order_by(LearnStackDomain.sort_order.desc()).first()
        sort_order = data.get("sort_order", (last.sort_order + 1) if last else 0)
        row = LearnStackDomain(
            name=name,
            description=data.get("description"),
            color=data.get("color"),
            sort_order=sort_order,
            is_active=data.get("is_active", True),
        )
        db.session.add(row)
        db.session.commit()
        return jsonify({"msg": "Domain created", "status": 1, "id": row.id, "domain": _domain_dict(row)}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": str(e), "status": 0}), 500


def update_domain(domain_id, decoded_payload=None):
    if not _admin_only(decoded_payload):
        return jsonify({"msg": "Admin only", "status": 0}), 403
    try:
        row = LearnStackDomain.query.get(domain_id)
        if not row:
            return jsonify({"msg": "Not found", "status": 0}), 404
        data = request.get_json() or {}
        if "name" in data:
            name = (data["name"] or "").strip()
            if name and name != row.name:
                if LearnStackDomain.query.filter_by(name=name).first():
                    return jsonify({"msg": "Domain name already exists", "status": 0}), 409
                row.name = name
        for key in ("description", "color", "sort_order", "is_active"):
            if key in data:
                setattr(row, key, data[key])
        db.session.commit()
        return jsonify({"msg": "Updated", "status": 1, "domain": _domain_dict(row)}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": str(e), "status": 0}), 500


def delete_domain(domain_id, decoded_payload=None):
    if not _admin_only(decoded_payload):
        return jsonify({"msg": "Admin only", "status": 0}), 403
    try:
        row = LearnStackDomain.query.get(domain_id)
        if not row:
            return jsonify({"msg": "Not found", "status": 0}), 404
        if LearnStackTechnology.query.filter_by(domain_id=domain_id).count():
            return jsonify({"msg": "Remove technologies first", "status": 0}), 400
        db.session.delete(row)
        db.session.commit()
        return jsonify({"msg": "Deleted", "status": 1}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": str(e), "status": 0}), 500


# --- Technologies (admin CRUD) ---


def list_technologies(decoded_payload=None):
    try:
        q = LearnStackTechnology.query.join(LearnStackDomain)
        domain_id = request.args.get("domain_id", type=int)
        if domain_id:
            q = q.filter(LearnStackTechnology.domain_id == domain_id)
        active_only = request.args.get("active_only", "1") == "1"
        if active_only and not _admin_only(decoded_payload):
            q = q.filter(LearnStackTechnology.is_active.is_(True))
        q = q.order_by(
            LearnStackTechnology.sort_order.asc(), LearnStackTechnology.name.asc()
        )
        rows = [_technology_dict(t) for t in q.all()]
        return jsonify({"technologies": rows, "status": 1}), 200
    except Exception as e:
        return jsonify({"msg": str(e), "status": 0}), 500


def create_technology(decoded_payload=None):
    if not _admin_only(decoded_payload):
        return jsonify({"msg": "Admin only", "status": 0}), 403
    try:
        data = request.get_json() or {}
        domain_id = data.get("domain_id")
        name = (data.get("name") or "").strip()
        if not domain_id or not name:
            return jsonify({"msg": "domain_id and name required", "status": 0}), 400
        if not LearnStackDomain.query.get(domain_id):
            return jsonify({"msg": "Invalid domain", "status": 0}), 400
        if LearnStackTechnology.query.filter_by(domain_id=domain_id, name=name).first():
            return jsonify({"msg": "Technology already exists for this domain", "status": 0}), 409
        last = (
            LearnStackTechnology.query.filter_by(domain_id=domain_id)
            .order_by(LearnStackTechnology.sort_order.desc())
            .first()
        )
        sort_order = data.get("sort_order", (last.sort_order + 1) if last else 0)
        row = LearnStackTechnology(
            domain_id=domain_id,
            name=name,
            description=data.get("description"),
            sort_order=sort_order,
            is_active=data.get("is_active", True),
        )
        db.session.add(row)
        db.session.commit()
        return (
            jsonify(
                {"msg": "Technology created", "status": 1, "id": row.id, "technology": _technology_dict(row)}
            ),
            201,
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": str(e), "status": 0}), 500


def update_technology(technology_id, decoded_payload=None):
    if not _admin_only(decoded_payload):
        return jsonify({"msg": "Admin only", "status": 0}), 403
    try:
        row = LearnStackTechnology.query.get(technology_id)
        if not row:
            return jsonify({"msg": "Not found", "status": 0}), 404
        data = request.get_json() or {}
        new_domain = data.get("domain_id")
        if new_domain is not None and new_domain != row.domain_id:
            if not LearnStackDomain.query.get(new_domain):
                return jsonify({"msg": "Invalid domain", "status": 0}), 400
            row.domain_id = new_domain
        if "name" in data:
            name = (data["name"] or "").strip()
            if name:
                clash = LearnStackTechnology.query.filter_by(
                    domain_id=row.domain_id, name=name
                ).first()
                if clash and clash.id != row.id:
                    return jsonify({"msg": "Name already exists in domain", "status": 0}), 409
                row.name = name
        for key in ("description", "sort_order", "is_active"):
            if key in data:
                setattr(row, key, data[key])
        db.session.commit()
        return jsonify({"msg": "Updated", "status": 1, "technology": _technology_dict(row)}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": str(e), "status": 0}), 500


def delete_technology(technology_id, decoded_payload=None):
    if not _admin_only(decoded_payload):
        return jsonify({"msg": "Admin only", "status": 0}), 403
    try:
        row = LearnStackTechnology.query.get(technology_id)
        if not row:
            return jsonify({"msg": "Not found", "status": 0}), 404
        if LearnStackCard.query.filter_by(technology_id=technology_id).count():
            return jsonify({"msg": "Technology is used on cards", "status": 0}), 400
        db.session.delete(row)
        db.session.commit()
        return jsonify({"msg": "Deleted", "status": 1}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": str(e), "status": 0}), 500


# --- Cards ---


def _replace_steps(card, steps_data):
    LearnStackStep.query.filter_by(card_id=card.id).delete()
    for i, raw in enumerate(steps_data or []):
        title = (raw.get("title") or "").strip() or f"Step {i + 1}"
        step = LearnStackStep(
            card_id=card.id,
            step_order=raw.get("step_order", i),
            title=title,
            body=raw.get("body") or raw.get("description"),
            image_url=raw.get("image_url"),
            document_url=raw.get("document_url"),
        )
        db.session.add(step)


def list_cards(decoded_payload=None):
    try:
        q = LearnStackCard.query
        domain_id = request.args.get("domain_id", type=int)
        technology_id = request.args.get("technology_id", type=int)
        search = (request.args.get("q") or "").strip().lower()
        mine = request.args.get("mine") == "1"
        if domain_id:
            q = q.filter_by(domain_id=domain_id)
        if technology_id:
            q = q.filter_by(technology_id=technology_id)
        if mine:
            q = q.filter_by(
                created_by_role_id=_jwt_role_id(decoded_payload),
                created_by_role=_jwt_role(decoded_payload),
            )
        elif not _admin_only(decoded_payload):
            q = q.filter_by(is_published=True)
        q = q.order_by(LearnStackCard.updated_at.desc())
        cards = q.all()
        if search:
            cards = [
                c
                for c in cards
                if search in (c.title or "").lower()
                or search in (c.description or "").lower()
            ]
        return jsonify(
            {
                "cards": [_card_summary(c, decoded_payload) for c in cards],
                "status": 1,
            }
        ), 200
    except Exception as e:
        return jsonify({"msg": str(e), "status": 0}), 500


def get_card(card_id, decoded_payload=None):
    try:
        card = LearnStackCard.query.get(card_id)
        if not card:
            return jsonify({"msg": "Not found", "status": 0}), 404
        if not card.is_published and not _can_edit_card(card, decoded_payload):
            return jsonify({"msg": "Not found", "status": 0}), 404
        return jsonify({"card": _card_detail(card, decoded_payload), "status": 1}), 200
    except Exception as e:
        return jsonify({"msg": str(e), "status": 0}), 500


def create_card(decoded_payload=None):
    try:
        data = request.get_json() or {}
        title = (data.get("title") or "").strip()
        domain_id = data.get("domain_id")
        technology_id = data.get("technology_id")
        if not title or not domain_id or not technology_id:
            return jsonify({"msg": "title, domain_id, technology_id required", "status": 0}), 400
        tech = LearnStackTechnology.query.get(technology_id)
        if not tech or tech.domain_id != int(domain_id):
            return jsonify({"msg": "Technology must belong to selected domain", "status": 0}), 400
        overview = data.get("overview_document_url")
        if data.get("overview_document_data"):
            overview = save_attachment(
                data.get("overview_document_data"),
                data.get("overview_document_name"),
                folder="learn_stack_docs",
            )
        card = LearnStackCard(
            domain_id=domain_id,
            technology_id=technology_id,
            title=title,
            description=data.get("description"),
            overview_document_url=overview,
            created_by_role_id=_jwt_role_id(decoded_payload),
            created_by_role=_jwt_role(decoded_payload),
            is_published=data.get("is_published", True),
        )
        db.session.add(card)
        db.session.flush()
        steps = data.get("steps") or []
        for i, raw in enumerate(steps):
            img = raw.get("image_url")
            if raw.get("image_data"):
                img = save_image(raw.get("image_data"), folder="learn_stack_images")
            doc = raw.get("document_url")
            if raw.get("document_data"):
                doc = save_attachment(
                    raw.get("document_data"),
                    raw.get("document_name"),
                    folder="learn_stack_docs",
                )
            steps[i] = {**raw, "image_url": img, "document_url": doc}
        _replace_steps(card, steps)
        db.session.commit()
        return jsonify(
            {"msg": "Card created", "status": 1, "id": card.id, "card": _card_detail(card, decoded_payload)}
        ), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": str(e), "status": 0}), 500


def update_card(card_id, decoded_payload=None):
    try:
        card = LearnStackCard.query.get(card_id)
        if not card:
            return jsonify({"msg": "Not found", "status": 0}), 404
        if not _can_edit_card(card, decoded_payload):
            return jsonify({"msg": "Forbidden", "status": 0}), 403
        data = request.get_json() or {}
        domain_id = data.get("domain_id", card.domain_id)
        technology_id = data.get("technology_id", card.technology_id)
        tech = LearnStackTechnology.query.get(technology_id)
        if not tech or tech.domain_id != int(domain_id):
            return jsonify({"msg": "Technology must belong to selected domain", "status": 0}), 400
        if "title" in data:
            card.title = (data["title"] or "").strip() or card.title
        if "description" in data:
            card.description = data["description"]
        card.domain_id = domain_id
        card.technology_id = technology_id
        if "is_published" in data and (_admin_only(decoded_payload) or data["is_published"] is not False):
            card.is_published = bool(data["is_published"])
        if "overview_document_data" in data and data["overview_document_data"]:
            if card.overview_document_url:
                delete_image(card.overview_document_url)
            card.overview_document_url = save_attachment(
                data["overview_document_data"],
                data.get("overview_document_name"),
                folder="learn_stack_docs",
            )
        elif "overview_document_url" in data:
            card.overview_document_url = data["overview_document_url"]
        if "steps" in data:
            steps = data["steps"] or []
            for i, raw in enumerate(steps):
                img = raw.get("image_url")
                if raw.get("image_data"):
                    img = save_image(raw.get("image_data"), folder="learn_stack_images")
                doc = raw.get("document_url")
                if raw.get("document_data"):
                    doc = save_attachment(
                        raw.get("document_data"),
                        raw.get("document_name"),
                        folder="learn_stack_docs",
                    )
                steps[i] = {**raw, "image_url": img, "document_url": doc}
            _replace_steps(card, steps)
        db.session.commit()
        return jsonify({"msg": "Updated", "status": 1, "card": _card_detail(card, decoded_payload)}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": str(e), "status": 0}), 500


def delete_card(card_id, decoded_payload=None):
    try:
        card = LearnStackCard.query.get(card_id)
        if not card:
            return jsonify({"msg": "Not found", "status": 0}), 404
        if not _can_edit_card(card, decoded_payload):
            return jsonify({"msg": "Forbidden", "status": 0}), 403
        if card.overview_document_url:
            delete_image(card.overview_document_url)
        for step in card.steps:
            if step.image_url:
                delete_image(step.image_url)
            if step.document_url:
                delete_image(step.document_url)
        db.session.delete(card)
        db.session.commit()
        return jsonify({"msg": "Deleted", "status": 1}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": str(e), "status": 0}), 500


def record_card_view(card_id, decoded_payload=None):
    try:
        card = LearnStackCard.query.get(card_id)
        if not card or (not card.is_published and not _can_edit_card(card, decoded_payload)):
            return jsonify({"msg": "Not found", "status": 0}), 404
        import datetime

        role_id = _jwt_role_id(decoded_payload)
        role = _jwt_role(decoded_payload)
        view = LearnStackView.query.filter_by(card_id=card_id, role_id=role_id, role=role).first()
        now = datetime.datetime.utcnow()
        if view:
            view.last_viewed_at = now
        else:
            view = LearnStackView(
                card_id=card_id, role_id=role_id, role=role, first_viewed_at=now, last_viewed_at=now
            )
            db.session.add(view)
        db.session.commit()
        readers = []
        for v in card.views.order_by(LearnStackView.last_viewed_at.desc()).limit(50):
            person = get_person_details(v.role, v.role_id)
            if person:
                readers.append(
                    {
                        **person,
                        "last_viewed_at": v.last_viewed_at.isoformat() if v.last_viewed_at else None,
                    }
                )
        return jsonify({"msg": "Recorded", "status": 1, "readers": readers, "view_count": card.views.count()}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": str(e), "status": 0}), 500


def toggle_card_like(card_id, decoded_payload=None):
    try:
        card = LearnStackCard.query.get(card_id)
        if not card or not card.is_published:
            return jsonify({"msg": "Not found", "status": 0}), 404
        role_id = _jwt_role_id(decoded_payload)
        role = _jwt_role(decoded_payload)
        like = LearnStackLike.query.filter_by(card_id=card_id, role_id=role_id, role=role).first()
        if like:
            db.session.delete(like)
            liked = False
        else:
            db.session.add(LearnStackLike(card_id=card_id, role_id=role_id, role=role))
            liked = True
        db.session.commit()
        return jsonify(
            {"status": 1, "liked": liked, "like_count": card.likes.count()}
        ), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": str(e), "status": 0}), 500


def list_comments(card_id, decoded_payload=None):
    try:
        card = LearnStackCard.query.get(card_id)
        if not card:
            return jsonify({"msg": "Not found", "status": 0}), 404
        rows = []
        for c in card.comments.order_by(LearnStackComment.created_at.asc()):
            author = get_person_details(c.role, c.role_id) or {}
            rows.append(
                {
                    "id": c.id,
                    "body": c.body,
                    "created_at": c.created_at.isoformat() if c.created_at else None,
                    "author": author,
                    "is_mine": c.role_id == _jwt_role_id(decoded_payload)
                    and c.role == _jwt_role(decoded_payload),
                }
            )
        return jsonify({"comments": rows, "status": 1}), 200
    except Exception as e:
        return jsonify({"msg": str(e), "status": 0}), 500


def add_comment(card_id, decoded_payload=None):
    try:
        card = LearnStackCard.query.get(card_id)
        if not card or not card.is_published:
            return jsonify({"msg": "Not found", "status": 0}), 404
        data = request.get_json() or {}
        body = (data.get("body") or "").strip()
        if not body:
            return jsonify({"msg": "Comment cannot be empty", "status": 0}), 400
        c = LearnStackComment(
            card_id=card_id,
            role_id=_jwt_role_id(decoded_payload),
            role=_jwt_role(decoded_payload),
            body=body,
        )
        db.session.add(c)
        db.session.commit()
        author = get_person_details(c.role, c.role_id) or {}
        return jsonify(
            {
                "status": 1,
                "comment": {
                    "id": c.id,
                    "body": c.body,
                    "created_at": c.created_at.isoformat() if c.created_at else None,
                    "author": author,
                    "is_mine": True,
                },
            }
        ), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": str(e), "status": 0}), 500


def delete_comment(card_id, comment_id, decoded_payload=None):
    try:
        c = LearnStackComment.query.filter_by(id=comment_id, card_id=card_id).first()
        if not c:
            return jsonify({"msg": "Not found", "status": 0}), 404
        is_owner = c.role_id == _jwt_role_id(decoded_payload) and c.role == _jwt_role(decoded_payload)
        if not is_owner and not _admin_only(decoded_payload):
            return jsonify({"msg": "Forbidden", "status": 0}), 403
        db.session.delete(c)
        db.session.commit()
        return jsonify({"msg": "Deleted", "status": 1}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": str(e), "status": 0}), 500


def upload_learn_stack_file(decoded_payload=None):
    try:
        if "file" not in request.files:
            return jsonify({"msg": "No file", "status": 0}), 400
        f = request.files["file"]
        if not f or not f.filename:
            return jsonify({"msg": "Empty file", "status": 0}), 400
        kind = (request.form.get("kind") or "document").strip().lower()
        folder = "learn_stack_images" if kind == "image" else "learn_stack_docs"
        ext = f.filename.rsplit(".", 1)[-1].lower() if "." in f.filename else "bin"
        filename = f"{uuid.uuid4()}.{ext}"
        base_path = current_app.config["SERVE_STATIC_FOLDER"]
        target_dir = os.path.join(base_path, folder)
        os.makedirs(target_dir, exist_ok=True)
        f.save(os.path.join(target_dir, filename))
        url = f"/src/assets/{folder}/{filename}"
        return jsonify({"status": 1, "url": url, "file_name": f.filename}), 200
    except Exception as e:
        return jsonify({"msg": str(e), "status": 0}), 500
