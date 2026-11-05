from datetime import datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import validates
from werkzeug.security import check_password_hash, generate_password_hash

from app.entity.db import db
from app.entity.encryption import EncryptedString, phone_digest


class UserAccount(db.Model):
    """Entity: a login account for any of the four actors."""

    ROLES = ("admin", "designer", "customer", "platform")

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), default="")
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(EncryptedString, default="")  # encrypted in the database
    phone_hash = db.Column(db.String(64), unique=True)  # keyed fingerprint, lets us find a taken number
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    is_suspended = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now)  # shown in UA-04, counted in PM-08
    must_change_password = db.Column(db.Boolean, default=False)  # set by a User Admin reset (UA-16)

    @validates("phone")
    def _fingerprint_phone(self, key, value):
        self.phone_hash = phone_digest(value)
        return value

    @classmethod
    def phone_exists(cls, phone, exclude_id=None):
        """Is this phone already on an account (other than exclude_id)?"""
        digest = phone_digest(phone)
        if digest is None:
            return False
        query = cls.query.filter_by(phone_hash=digest)
        if exclude_id is not None:
            query = query.filter(cls.id != exclude_id)
        return query.first() is not None

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password or "")

    def change_password(self, new_password):
        self.set_password(new_password)
        self.must_change_password = False
        db.session.commit()

    def update_details(self, name, email, phone):
        self.name, self.email, self.phone = name, email, phone
        db.session.commit()

    # --- Customer profile form ---------------------------------------------
    # Names are stored as one string; the form shows the last word as the
    # last name ("Wei Ming Tan" -> "Wei Ming" + "Tan").

    @property
    def first_name(self):
        parts = (self.name or "").rsplit(" ", 1)
        return parts[0] if len(parts) == 2 else (self.name or "")

    @property
    def last_name(self):
        parts = (self.name or "").rsplit(" ", 1)
        return parts[1] if len(parts) == 2 else ""

    @classmethod
    def create(cls, email, password, role, name="", phone="", must_change_password=False):
        from app.entity.user_profile import UserProfile

        if role not in cls.ROLES and UserProfile.by_key(role) is None:
            raise ValueError(f"Unknown role: {role}")
        account = cls(email=email, role=role, name=name, phone=phone,
                      must_change_password=must_change_password)
        account.set_password(password)
        db.session.add(account)
        try:
            db.session.commit()
        except IntegrityError:
            # Two sign-ups passed the "is it taken?" check together and the unique index caught the second.
            db.session.rollback()
            if cls.email_exists(email):
                raise ValueError("Email already registered.") from None
            if cls.phone_exists(phone):
                raise ValueError("Phone number already registered.") from None
            raise  # something else is wrong with the data: do not hide it
        return account

    @classmethod
    def get(cls, account_id):
        return db.session.get(cls, account_id)

    @classmethod
    def count_by_role(cls, role):
        return cls.query.filter_by(role=role, is_suspended=False).count()

    # --- Designer public profile -------------------------------------------
    # `designer_application` is the approved DesignerApplication that created
    # this account (set up as a backref in designer_application.py). Designers
    # created without an application fall back to their personal name.

    @property
    def company(self):
        from app.entity.designer_company import DesignerCompany

        company = DesignerCompany.for_account(self.id)

        if company:
            return company

        if DesignerCompany.was_removed(self.id):
            return None

        return getattr(self, "designer_application", None)

    @property
    def display_name(self):
        return self.company.company_name if self.company else self.name

    @property
    def initials(self):
        words = [w for w in self.display_name.replace("&", " ").split() if w[0].isalnum()]
        return "".join(w[0] for w in words[:2]).upper() or "?"

    @property
    def designer_since(self):
        return self.company.reviewed_at.year if self.company and self.company.reviewed_at else None

    @classmethod
    def email_exists(cls, email):
        return cls.query.filter_by(email=email).first() is not None

    @classmethod
    def find_by_email(cls, email):
        return cls.query.filter_by(email=email).first()

    @classmethod
    def login(cls, email, password):
        """Return the account if the credentials are valid and active, else None."""
        account = cls.query.filter_by(email=email).first()
        if account is None or account.is_blocked:
            return None
        if not check_password_hash(account.password_hash, password):
            return None
        return account


    # --- User Admin account management (UA-03 to UA-07, UA-11, UA-13, UA-16) ----

    @property
    def profile(self):
        """The UserProfile (role) this account is assigned to."""
        from app.entity.user_profile import UserProfile

        return UserProfile.by_key(self.role)

    @property
    def profile_name(self):
        return self.profile.name if self.profile else self.role.title()

    @property
    def is_blocked(self):
        """Cannot log in: the account (UA-06) or its whole profile (UA-11) is suspended."""
        from app.entity.user_profile import UserProfile

        return bool(self.is_suspended) or UserProfile.is_key_suspended(self.role)

    @property
    def status(self):
        return "Suspended" if self.is_suspended else "Active"

    @classmethod
    def email_taken_by_other(cls, email, account_id):
        return cls.query.filter(cls.email == email, cls.id != account_id).first() is not None

    @classmethod
    def search(cls, keyword="", role=None, status=None):
        query = cls.query
        if keyword:
            query = query.filter(db.or_(cls.name.icontains(keyword, autoescape=True), cls.email.icontains(keyword, autoescape=True)))
        if role:
            query = query.filter(cls.role == role)
        if status in ("active", "suspended"):
            query = query.filter(cls.is_suspended.is_(status == "suspended"))
        return query.order_by(cls.name, cls.email).all()

    def update_by_admin(self, name, email, phone, role):
        self.name, self.email, self.phone, self.role = name, email, phone, role
        db.session.commit()

    def set_suspended(self, suspended):
        self.is_suspended = suspended
        db.session.commit()

    def reset_password(self, temporary_password):
        self.set_password(temporary_password)
        self.must_change_password = True
        db.session.commit()
