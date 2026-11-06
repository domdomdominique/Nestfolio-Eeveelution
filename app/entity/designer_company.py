from app.entity.db import db
from app.entity.encryption import EncryptedString


class DesignerCompany(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    account_id = db.Column(
        db.Integer,
        db.ForeignKey("user_account.id"),
        unique=True,
        nullable=False,
    )

    company_name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, default="")
    address = db.Column(db.String(255), default="")
    phone = db.Column(EncryptedString, default="")
    email = db.Column(db.String(120), default="")

    uen = db.Column(db.String(20), default="")
    portfolio_url = db.Column(db.String(255), default="")
    experience_years = db.Column(db.Integer, default=0)
    reviewed_at = db.Column(db.DateTime)
    profile_photo = db.relationship(
        "CompanyProfilePhoto",
        uselist=False,
        cascade="all, delete-orphan",
        backref="company",
    )
    # Wide banner shown across the top of the public designer profile.
    cover_photo = db.relationship(
        "CompanyCoverPhoto",
        uselist=False,
        cascade="all, delete-orphan",
        backref="company",
    )

    @classmethod
    def for_account(cls, account_id):
        return cls.query.filter_by(account_id=account_id).first()

    @classmethod
    def was_removed(cls, account_id):
        return db.session.get(CompanyRemoval, account_id) is not None

    @classmethod
    def create(cls, account_id, photo=None, cover=None, **details):
        company = cls(account_id=account_id, **details)
        if photo is not None:
            company.profile_photo = CompanyProfilePhoto(**photo)
        if cover is not None:
            company.cover_photo = CompanyCoverPhoto(**cover)
        db.session.add(company)

        CompanyRemoval.query.filter_by(
            account_id=account_id
        ).delete(synchronize_session=False)

        db.session.commit()
        return company

    @classmethod
    def save(cls, account, details, photo=None, remove_photo=False,
             cover=None, remove_cover=False):
        company = cls.for_account(account.id)

        if company is None:
            company = cls(account_id=account.id)

            application = getattr(
                account, "designer_application", None
            )

            if application:
                for field in (
                    "uen",
                    "portfolio_url",
                    "experience_years",
                    "reviewed_at",
                ):
                    setattr(
                        company,
                        field,
                        getattr(application, field),
                    )

            db.session.add(company)

        for field, value in details.items():
            setattr(company, field, value)

        if remove_photo:
            company.profile_photo = None

        if photo is not None:
            if company.profile_photo is None:
                company.profile_photo = CompanyProfilePhoto(**photo)
            else:
                company.profile_photo.filename = photo["filename"]
                company.profile_photo.content_type = photo["content_type"]
                company.profile_photo.data = photo["data"]

        if remove_cover:
            company.cover_photo = None

        if cover is not None:
            if company.cover_photo is None:
                company.cover_photo = CompanyCoverPhoto(**cover)
            else:
                company.cover_photo.filename = cover["filename"]
                company.cover_photo.content_type = cover["content_type"]
                company.cover_photo.data = cover["data"]

        CompanyRemoval.query.filter_by(
            account_id=account.id
        ).delete(synchronize_session=False)

        db.session.commit()
        return company

    @classmethod
    def delete_for(cls, account_id):
        company = cls.for_account(account_id)

        if company is not None:
            db.session.delete(company)

        if not cls.was_removed(account_id):
            db.session.add(
                CompanyRemoval(account_id=account_id)
            )

        db.session.commit()


class CompanyRemoval(db.Model):
    account_id = db.Column(
        db.Integer,
        db.ForeignKey("user_account.id"),
        primary_key=True,
    )

class CompanyProfilePhoto(db.Model):
    company_id = db.Column(
        db.Integer,
        db.ForeignKey("designer_company.id"),
        primary_key=True,
    )
    filename = db.Column(db.String(255), nullable=False)
    content_type = db.Column(db.String(30), nullable=False)
    data = db.deferred(
        db.Column(db.LargeBinary, nullable=False)
    )


class CompanyCoverPhoto(db.Model):
    company_id = db.Column(
        db.Integer,
        db.ForeignKey("designer_company.id"),
        primary_key=True,
    )
    filename = db.Column(db.String(255), nullable=False)
    content_type = db.Column(db.String(30), nullable=False)
    data = db.deferred(
        db.Column(db.LargeBinary, nullable=False)
    )
