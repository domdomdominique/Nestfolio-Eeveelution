from datetime import datetime

from app.entity.db import db


class UserProfile(db.Model):
    """Entity: a user profile, i.e. a role accounts are assigned to (UA-08 to UA-12).

    `key` is what UserAccount.role stores and never changes, so renaming a
    profile (UA-10) shows the new name on every account using it.
    """

    STATUSES = ("active", "suspended")
    ADMIN_KEY = "admin"  # this profile can never be suspended (UA-11)

    DEFAULTS = (
        ("admin", "User Admin", "Manages user accounts, profiles and reported projects."),
        ("platform", "Platform Management", "Manages IDP categories and platform reports."),
        ("designer", "Interior Designer", "Publishes interior design projects (IDPs)."),
        ("customer", "Customer", "Browses, saves and enquires about IDPs."),
    )

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.Text, default="")
    status = db.Column(db.String(20), default="active", nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

    @classmethod
    def ensure_defaults(cls):
        existing = {key for (key,) in db.session.query(cls.key)}
        for key, name, description in cls.DEFAULTS:
            if key not in existing:
                db.session.add(cls(key=key, name=name, description=description))
        db.session.commit()

    @classmethod
    def get(cls, profile_id):
        return db.session.get(cls, profile_id)

    @classmethod
    def by_key(cls, key):
        return cls.query.filter_by(key=key).first()

    @classmethod
    def name_exists(cls, name, exclude_id=None):
        query = cls.query.filter(db.func.lower(cls.name) == name.lower())
        if exclude_id is not None:
            query = query.filter(cls.id != exclude_id)
        return query.first() is not None

    @classmethod
    def create(cls, name, description=""):
        key = base = "".join(ch for ch in name.lower() if ch.isalnum())[:20] or "profile"
        n = 2
        while cls.by_key(key):
            key, n = f"{base[:18]}{n}", n + 1
        profile = cls(key=key, name=name, description=description)
        db.session.add(profile)
        db.session.commit()
        return profile

    @classmethod
    def list_all(cls, keyword=""):
        query = cls.query
        if keyword:
            query = query.filter(cls.name.icontains(keyword, autoescape=True))
        return query.order_by(cls.id).all()

    @classmethod
    def active(cls):
        return cls.query.filter_by(status="active").order_by(cls.id).all()

    @classmethod
    def is_key_suspended(cls, key):
        profile = cls.by_key(key)
        return profile is not None and profile.status == "suspended"

    @property
    def is_active(self):
        return self.status == "active"

    @property
    def account_count(self):
        from app.entity.user_account import UserAccount

        return UserAccount.query.filter_by(role=self.key).count()

    def update(self, name, description):
        self.name, self.description = name, description
        db.session.commit()

    def suspend(self):
        # UA-11 The User Admin profile can never be suspended, and a suspended profile cannot be suspended again.
        if self.key == self.ADMIN_KEY:
            raise ValueError("The User Admin profile cannot be suspended.")
        if self.status == "suspended":
            raise ValueError("This profile is already suspended.")
        self.status = "suspended"
        db.session.commit()
