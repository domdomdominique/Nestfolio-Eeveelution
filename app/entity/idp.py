import random
from datetime import date, datetime

from app.entity.db import db


class IDP(db.Model):
    """Entity: an Interior Design Project in a designer's portfolio."""

    CATEGORIES = ("Living Room", "Kitchen", "Bedroom", "Bathroom", "Study & Office", "Whole Home")

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, default="")
    category = db.Column(db.String(50), nullable=False)
    designer_id = db.Column(db.Integer, db.ForeignKey("user_account.id"), nullable=False)
    view_count = db.Column(db.Integer, default=0)
    shortlist_count = db.Column(db.Integer, default=0)
    is_current = db.Column(db.Boolean, default=False)  # current (in progress) vs past project
    created_at = db.Column(db.DateTime, default=datetime.now)
    is_removed = db.Column(db.Boolean, default=False)  # hidden by a User Admin (UA-17)

    designer = db.relationship("UserAccount")
    view_events = db.relationship(
        "IDPView",
        cascade="all, delete-orphan",
    )
    photos = db.relationship(
        "IDPPhoto",
        cascade="all, delete-orphan",
        order_by="IDPPhoto.id",
        backref="idp",
    )

    @classmethod
    def categories(cls):
        """The categories a designer may pick (ID-12) and customers filter by (C-05).

        Managed by Platform Management (PM-03 to PM-06); CATEGORIES above are
        only the defaults created on first run.
        """
        from app.entity.idp_category import IDPCategory

        return IDPCategory.names()

    @classmethod
    def get(cls, idp_id):
        return db.session.get(cls, idp_id)

    @classmethod
    def visible(cls, query=None):
        """Only IDPs customers may see: designer active (C-04) and not removed by an admin (UA-17)."""
        from app.entity.user_account import UserAccount

        query = cls.query if query is None else query
        return (query.join(UserAccount, cls.designer_id == UserAccount.id)
                .filter(UserAccount.is_suspended.isnot(True), cls.is_removed.isnot(True)))

    @property
    def is_visible(self):
        return not (self.is_removed or (self.designer and self.designer.is_suspended))

    @classmethod
    def search(cls, keyword):
        """Case-insensitive search on title or category."""
        if not keyword:
            return cls.query.order_by(cls.id).all()
        return (
            cls.query.filter(db.or_(cls.title.icontains(keyword, autoescape=True), cls.category.icontains(keyword, autoescape=True)))
            .order_by(cls.id)
            .all()
        )

    @classmethod
    def browse(cls, keyword="", categories=(), status=None, sort="recommended"):
        """Search projects using the current company information."""
        from app.entity.designer_application import DesignerApplication
        from app.entity.designer_company import DesignerCompany, CompanyRemoval
        from app.entity.user_account import UserAccount

        query = cls.visible()

        if keyword:
            company_name = db.case(
                (
                    DesignerCompany.id.isnot(None),
                    DesignerCompany.company_name,
                ),
                (
                    CompanyRemoval.account_id.isnot(None),
                    None,
                ),
                else_=DesignerApplication.company_name,
            )

            query = (
                query.outerjoin(
                    DesignerApplication,
                    DesignerApplication.account_id == UserAccount.id,
                )
                .outerjoin(
                    DesignerCompany,
                    DesignerCompany.account_id == UserAccount.id,
                )
                .outerjoin(
                    CompanyRemoval,
                    CompanyRemoval.account_id == UserAccount.id,
                )
                .filter(
                    db.or_(
                        cls.title.icontains(keyword, autoescape=True),
                        cls.description.icontains(keyword, autoescape=True),
                        cls.category.icontains(keyword, autoescape=True),
                        UserAccount.name.icontains(keyword, autoescape=True),
                        company_name.icontains(keyword, autoescape=True),
                    )
                )
            )

        if categories:
            query = query.filter(cls.category.in_(categories))

        if status in ("current", "past"):
            query = query.filter(
                cls.is_current == (status == "current")
            )

        if sort == "recommended":
            return cls._by_fair_score(query)

        order = (
            cls.created_at.desc()
            if sort == "newest"
            else cls.view_count.desc()
        )

        return query.order_by(order, cls.id.desc()).all()

    @classmethod
    def count_by_status(cls):
        current = cls.visible().filter(cls.is_current.is_(True)).count()
        return {"current": current, "past": cls.visible().count() - current}

    @classmethod
    def more_by_designer(cls, designer_id, exclude_id, limit=4):
        """The designer's other projects, most viewed first."""
        return (
            cls.visible().filter(cls.designer_id == designer_id, cls.id != exclude_id)
            .order_by(cls.view_count.desc(), cls.id.desc())
            .limit(limit)
            .all()
        )

    def record_view(self):
        from app.entity.idp_view import IDPView

        self.view_count = (
            db.func.coalesce(IDP.view_count, 0) + 1
        )

        db.session.add(
            IDPView(
                idp_id=self.id,
                category=self.category,
            )
        )

        db.session.commit()

    def remove(self):
        """Hide from customers after a report (UA-17); the designer still has it."""
        self.is_removed = True
        db.session.commit()

    # Fair ranking: views per day since posting, with a head start (FAIR_DAYS) so a brand-new
    # project is judged on how much attention it gets, not on how long it has been online.
    FAIR_DAYS = 7

    def fair_score(self, now=None):
        age_days = max(0, ((now or datetime.now()) - (self.created_at or datetime.now())).days)
        return (self.view_count or 0) / (age_days + self.FAIR_DAYS)

    @classmethod
    def _by_fair_score(cls, query):
        """Highest fair score first; ties (e.g. no views yet) go to the newest project."""
        now = datetime.now()
        projects = query.order_by(cls.id.desc()).all()
        return sorted(projects, key=lambda p: p.fair_score(now), reverse=True)

    @classmethod
    def popular(cls, sort="recommended", limit=4):
        """Recommended (default, fair to new projects), most viewed, or newest projects."""
        if sort == "recommended":
            return cls._by_fair_score(cls.visible())[:limit]
        order = cls.created_at.desc() if sort == "newest" else cls.view_count.desc()
        return cls.visible().order_by(order, cls.id.desc()).limit(limit).all()

    @classmethod
    def count_by_category(cls):
        rows = cls.visible(db.session.query(cls.category, db.func.count(cls.id))).group_by(cls.category)
        return dict(rows.all())

    @classmethod
    def top_designer_ids(cls, limit=3):
        """IDs of the (active) designers with the most projects."""
        rows = (
            cls.visible(db.session.query(cls.designer_id))
            .group_by(cls.designer_id)
            .order_by(db.func.count(cls.id).desc(), cls.designer_id)
            .limit(limit)
        )
        return [designer_id for (designer_id,) in rows]

    @classmethod
    def featured_designer_ids(cls, limit=3):
        """Designers shown on the landing page: any active designer with a visible project,
        rotated daily so small and new studios get their turn, not just the busiest."""
        rows = cls.visible(db.session.query(cls.designer_id)).group_by(cls.designer_id).order_by(cls.designer_id)
        ids = [designer_id for (designer_id,) in rows]
        random.Random(date.today().toordinal()).shuffle(ids)
        return ids[:limit]

    @classmethod
    def by_designer(cls, designer_id, status=None):
        """A designer's projects; status is None (all), 'current' or 'past'."""
        query = cls.query.filter_by(designer_id=designer_id)
        if status in ("current", "past"):
            query = query.filter_by(is_current=(status == "current"))
        return query.order_by(cls.is_current.desc(), cls.view_count.desc()).all()

    @classmethod
    def count_for_designer(cls, designer_id):
        return cls.query.filter_by(designer_id=designer_id).count()


    @classmethod
    def create_for_designer(
        cls,
        designer_id,
        title,
        description,
        category,
        is_current,
        photos=(),
    ):
        project = cls(
            designer_id=designer_id,
            title=title,
            description=description,
            category=category,
            is_current=is_current,
        )

        db.session.add(project)
        project._attach_photos(photos)
        db.session.commit()

        return project

    def _attach_photos(self, photos):
        from app.entity.idp_photo import IDPPhoto

        self.photos.extend(
            IDPPhoto(**photo)
            for photo in photos
        )

    def update_details(
        self,
        title,
        description,
        category,
        is_current,
        photos=(),
    ):
        self.title = title
        self.description = description
        self.category = category
        self.is_current = is_current

        self._attach_photos(photos)
        db.session.commit()

    def delete_project(self):
        from app.entity.enquiry import Enquiry
        from app.entity.favourite import Favourite
        from app.entity.report import Report

        # Keep enquiries, but remove their deleted-project link.
        Enquiry.query.filter_by(idp_id=self.id).update(
            {"idp_id": None},
            synchronize_session="fetch",
        )

        Favourite.query.filter_by(idp_id=self.id).delete(
            synchronize_session="fetch"
        )

        Report.query.filter_by(idp_id=self.id).delete(
            synchronize_session="fetch"
        )

        db.session.delete(self)
        db.session.commit()


    @classmethod
    def search_for_designer(cls, designer_id, keyword):
        keyword = (keyword or "").strip()

        query = cls.query.filter_by(
            designer_id=designer_id
        )

        if keyword:
            query = query.filter(
                db.or_(
                    cls.title.icontains(
                        keyword,
                        autoescape=True,
                    ),
                    cls.category.icontains(
                        keyword,
                        autoescape=True,
                    ),
                    cls.description.icontains(
                        keyword,
                        autoescape=True,
                    ),
                )
            )

        return query.order_by(
            cls.is_current.desc(),
            cls.view_count.desc(),
            cls.id.desc(),
        ).all()

    @classmethod
    def get_owned(cls, idp_id, designer_id):
        return cls.query.filter_by(
            id=idp_id,
            designer_id=designer_id,
        ).first()

    @classmethod
    def create(cls, designer_id, title, description, category, is_current):
        return cls.create_for_designer(
            designer_id, title, description, category, is_current
        )

    def update(self, title, description, category, is_current):
        self.update_details(title, description, category, is_current)

    def set_current(self, is_current):
        self.is_current = is_current
        db.session.commit()

    def delete(self):
        self.delete_project()

    @classmethod
    def _portfolio_query(cls, designer_id, keyword="", status=None, category=None):
        query = cls.query.filter_by(designer_id=designer_id)
        if keyword:
            query = query.filter(
                db.or_(
                    cls.title.icontains(keyword, autoescape=True),
                    cls.category.icontains(keyword, autoescape=True),
                    cls.description.icontains(keyword, autoescape=True),
                )
            )
        if status in ("current", "past"):
            query = query.filter(cls.is_current == (status == "current"))
        if category:
            query = query.filter(cls.category == category)
        return query

    @classmethod
    def portfolio(cls, designer_id, keyword="", status=None, category=None, limit=None, offset=0):
        """A designer's own projects, newest first, filtered by keyword, status and category."""
        query = (cls._portfolio_query(designer_id, keyword, status, category)
                 .order_by(cls.created_at.desc(), cls.id.desc()).offset(offset))
        return (query.limit(limit) if limit else query).all()

    @classmethod
    def portfolio_count(cls, designer_id, keyword="", status=None, category=None):
        return cls._portfolio_query(designer_id, keyword, status, category).count()

    @classmethod
    def top_for_designer(cls, designer_id, limit=5):
        """A designer's most viewed projects."""
        return (cls.query.filter_by(designer_id=designer_id)
                .order_by(cls.view_count.desc(), cls.id.desc()).limit(limit).all())

    @classmethod
    def added_since(cls, designer_id, since):
        return cls.query.filter(cls.designer_id == designer_id, cls.created_at >= since).count()

    @classmethod
    def status_counts_for_designer(cls, designer_id):
        total = cls.count_for_designer(designer_id)
        current = cls.query.filter_by(designer_id=designer_id, is_current=True).count()
        return {"all": total, "current": current, "past": total - current}

    @classmethod
    def totals_for_designer(cls, designer_id):
        """Summed views and shortlists across a designer's projects (ID-13, ID-14)."""
        views, shortlists = db.session.query(
            db.func.coalesce(db.func.sum(cls.view_count), 0),
            db.func.coalesce(db.func.sum(cls.shortlist_count), 0),
        ).filter(cls.designer_id == designer_id).one()
        return {"views": int(views), "shortlists": int(shortlists)}
