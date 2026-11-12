import datetime
from src import db


class LearnStackDomain(db.Model):
    __tablename__ = "learn_stack_domains"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(120), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)
    color = db.Column(db.String(32), nullable=True)
    sort_order = db.Column(db.Integer, default=0, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow
    )

    technologies = db.relationship(
        "LearnStackTechnology", back_populates="domain", lazy="dynamic"
    )


class LearnStackTechnology(db.Model):
    __tablename__ = "learn_stack_technologies"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    domain_id = db.Column(
        db.Integer, db.ForeignKey("learn_stack_domains.id"), nullable=False, index=True
    )
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=True)
    sort_order = db.Column(db.Integer, default=0, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow
    )

    domain = db.relationship("LearnStackDomain", back_populates="technologies")
    cards = db.relationship("LearnStackCard", back_populates="technology", lazy="dynamic")

    __table_args__ = (
        db.UniqueConstraint("domain_id", "name", name="uq_learn_stack_tech_domain_name"),
    )


class LearnStackCard(db.Model):
    __tablename__ = "learn_stack_cards"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    domain_id = db.Column(
        db.Integer, db.ForeignKey("learn_stack_domains.id"), nullable=False, index=True
    )
    technology_id = db.Column(
        db.Integer, db.ForeignKey("learn_stack_technologies.id"), nullable=False, index=True
    )
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    overview_document_url = db.Column(db.String(512), nullable=True)
    created_by_role_id = db.Column(db.Integer, nullable=False, index=True)
    created_by_role = db.Column(db.String(32), nullable=False)
    is_published = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow
    )

    domain = db.relationship("LearnStackDomain")
    technology = db.relationship("LearnStackTechnology", back_populates="cards")
    steps = db.relationship(
        "LearnStackStep",
        back_populates="card",
        lazy="dynamic",
        cascade="all, delete-orphan",
        order_by="LearnStackStep.step_order",
    )
    likes = db.relationship(
        "LearnStackLike", back_populates="card", lazy="dynamic", cascade="all, delete-orphan"
    )
    comments = db.relationship(
        "LearnStackComment", back_populates="card", lazy="dynamic", cascade="all, delete-orphan"
    )
    views = db.relationship(
        "LearnStackView", back_populates="card", lazy="dynamic", cascade="all, delete-orphan"
    )


class LearnStackStep(db.Model):
    __tablename__ = "learn_stack_steps"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    card_id = db.Column(
        db.Integer, db.ForeignKey("learn_stack_cards.id"), nullable=False, index=True
    )
    step_order = db.Column(db.Integer, default=0, nullable=False)
    title = db.Column(db.String(255), nullable=False)
    body = db.Column(db.Text, nullable=True)
    image_url = db.Column(db.String(512), nullable=True)
    document_url = db.Column(db.String(512), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    card = db.relationship("LearnStackCard", back_populates="steps")


class LearnStackLike(db.Model):
    __tablename__ = "learn_stack_likes"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    card_id = db.Column(
        db.Integer, db.ForeignKey("learn_stack_cards.id"), nullable=False, index=True
    )
    role_id = db.Column(db.Integer, nullable=False, index=True)
    role = db.Column(db.String(32), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    card = db.relationship("LearnStackCard", back_populates="likes")

    __table_args__ = (
        db.UniqueConstraint("card_id", "role_id", "role", name="uq_learn_stack_like_user"),
    )


class LearnStackComment(db.Model):
    __tablename__ = "learn_stack_comments"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    card_id = db.Column(
        db.Integer, db.ForeignKey("learn_stack_cards.id"), nullable=False, index=True
    )
    role_id = db.Column(db.Integer, nullable=False, index=True)
    role = db.Column(db.String(32), nullable=False)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow
    )

    card = db.relationship("LearnStackCard", back_populates="comments")


class LearnStackView(db.Model):
    __tablename__ = "learn_stack_views"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    card_id = db.Column(
        db.Integer, db.ForeignKey("learn_stack_cards.id"), nullable=False, index=True
    )
    role_id = db.Column(db.Integer, nullable=False, index=True)
    role = db.Column(db.String(32), nullable=False)
    first_viewed_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    last_viewed_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    card = db.relationship("LearnStackCard", back_populates="views")

    __table_args__ = (
        db.UniqueConstraint("card_id", "role_id", "role", name="uq_learn_stack_view_user"),
    )
