import hashlib
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class Permission:
    VIEW = 1
    COMMENT = 2
    CREATE_POST = 4
    MODERATE = 8
    ADMIN = 16

class Role(db.Model):
    __tablename__ = "roles"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Unicode(30), unique=True, nullable=False)
    permissions = db.Column(db.Integer, nullable=False, default=0)

    users = db.relationship("User", back_populates="role")

    def add_permission(self, perm):
        if not self.has_permission(perm):
            self.permissions += perm

    def has_permission(self, perm):
        return (self.permissions & perm) == perm

    @staticmethod
    def insert_roles():
        roles = {
            "Member": Permission.VIEW | Permission.COMMENT,
            "Reviewer": Permission.VIEW | Permission.COMMENT | Permission.CREATE_POST,
            "Admin": Permission.VIEW | Permission.COMMENT | Permission.CREATE_POST | Permission.MODERATE | Permission.ADMIN
        }
        for name, perms in roles.items():
            role = Role.query.filter_by(name=name).first()
            if role is None:
                role = Role(name=name)
            role.permissions = perms
            db.session.add(role)
        db.session.commit()

class Follow(db.Model):
    __tablename__ = "follows"

    follower_id = db.Column(db.Integer, db.ForeignKey("users.id"), primary_key=True)
    followed_id = db.Column(db.Integer, db.ForeignKey("users.id"), primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.Unicode(120), unique=True, nullable=False, index=True)
    username = db.Column(db.Unicode(50), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.Unicode(255), nullable=False)
    is_verified = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"))
    role = db.relationship("Role", back_populates="users")

    posts = db.relationship("Post", back_populates="author", lazy="dynamic")
    reviews = db.relationship("ReviewComment", back_populates="author", lazy="dynamic")
    post_comments = db.relationship("PostComment", back_populates="author", lazy="dynamic")

    def can(self, perm):
        return self.role is not None and self.role.has_permission(perm)

    def is_admin(self):
        return self.can(Permission.ADMIN)

    def gravatar_url(self, size=80):
        email_hash = hashlib.md5(self.email.strip().lower().encode("utf-8")).hexdigest()
        return f"https://www.gravatar.com/avatar/{email_hash}?d=identicon&s={size}"

    def follow(self, user):
        if not self.is_following(user) and user.id != self.id:
            db.session.add(Follow(follower_id=self.id, followed_id=user.id))

    def unfollow(self, user):
        f = Follow.query.filter_by(follower_id=self.id, followed_id=user.id).first()
        if f:
            db.session.delete(f)

    def is_following(self, user):
        return Follow.query.filter_by(follower_id=self.id, followed_id=user.id).first() is not None

    @property
    def followed_posts(self):
        return (Post.query
                .join(Follow, Follow.followed_id == Post.author_id)
                .filter(Follow.follower_id == self.id)
                .order_by(Post.created_at.desc()))

    def set_password(self, raw_password):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password_hash, raw_password)

class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Unicode(80), unique=True, nullable=False, index=True)

    devices = db.relationship("Device", back_populates="category")

class Brand(db.Model):
    __tablename__ = "brands"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Unicode(80), unique=True, nullable=False, index=True)

    devices = db.relationship("Device", back_populates="brand")

class Device(db.Model):
    __tablename__ = "devices"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Unicode(200), nullable=False, index=True)
    price = db.Column(db.Integer, nullable=False, default=0)
    specs = db.Column(db.UnicodeText, nullable=True)
    image_url = db.Column(db.Unicode(500), nullable=True)
    is_deleted = db.Column(db.Boolean, nullable=False, default=False)

    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False)
    brand_id = db.Column(db.Integer, db.ForeignKey("brands.id"), nullable=False)

    category = db.relationship("Category", back_populates="devices")
    brand = db.relationship("Brand", back_populates="devices")
    reviews = db.relationship("ReviewComment", back_populates="device", cascade="all, delete-orphan")

class Post(db.Model):
    __tablename__ = "posts"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.Unicode(200), nullable=False)
    image_url = db.Column(db.Unicode(500), nullable=True)
    body_md = db.Column(db.UnicodeText, nullable=False)
    body_html = db.Column(db.UnicodeText, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    author = db.relationship("User", back_populates="posts")
    comments = db.relationship("PostComment", back_populates="post", cascade="all, delete-orphan", order_by="PostComment.created_at.desc()")

class PostComment(db.Model):
    __tablename__ = "post_comments"

    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("posts.id"), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    body_md = db.Column(db.UnicodeText, nullable=False)
    body_html = db.Column(db.UnicodeText, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    post = db.relationship("Post", back_populates="comments")
    author = db.relationship("User", back_populates="post_comments")

class ReviewComment(db.Model):
    __tablename__ = "review_comments"

    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey("devices.id"), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    body_md = db.Column(db.UnicodeText, nullable=False)
    body_html = db.Column(db.UnicodeText, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    device = db.relationship("Device", back_populates="reviews")
    author = db.relationship("User", back_populates="reviews")
