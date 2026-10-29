"""Generate test data: 100 records per data type, plus one known login per role.

Run:  python seed.py
"""
import random
from datetime import datetime, timedelta

from werkzeug.security import generate_password_hash

from app import create_app
from app.entity.announcement import Announcement
from app.entity.db import db
from app.entity.designer_application import DesignerApplication
from app.entity.enquiry import Enquiry
from app.entity.favourite import Favourite
from app.entity.idp import IDP
from app.entity.idp_category import IDPCategory
from app.entity.idp_view import IDPView
from app.entity.report import Report
from app.entity.user_account import UserAccount
from app.entity.user_profile import UserProfile

STYLES = ["Scandinavian", "Industrial", "Modern", "Minimalist", "Japandi", "Classic", "Tropical"]
PLACES = ["HDB 4-room", "HDB 5-room", "Condo", "Landed House", "Loft", "Shophouse"]
FIRST_NAMES = ["Wei Ming", "Hui Min", "Jun Jie", "Xin Yi", "Ahmad", "Nur Aisyah", "Rajesh",
               "Priya", "Daniel", "Rachel", "Marcus", "Chloe", "Ethan", "Grace", "Farhan", "Divya"]
LAST_NAMES = ["Tan", "Lim", "Lee", "Ng", "Wong", "Goh", "Ong", "Koh", "Teo", "Rahman",
              "Ismail", "Kumar", "Singh", "Nair", "Chen", "Chua"]
COMPANY_WORDS = ["Oak", "Nest", "Haus", "Atelier", "Linea", "Terra", "Mosaic", "Ember", "Blanc", "Zen"]
COMPANY_TYPES = ["Interiors", "Design Studio", "Living", "Concepts", "Spaces"]

random.seed(314)  # same data every run, so demos are repeatable


def random_name():
    return f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"


_used_emails = set()


def email_for(name):
    """The whole name run together, e.g. "Wei Ming Tan" -> weimingtan@test.com.
    Emails must be unique, so a repeated name gets a number: weimingtan2@test.com."""
    base = name.replace(" ", "").lower()
    email, n = f"{base}@test.com", 1
    while email in _used_emails:
        n += 1
        email = f"{base}{n}@test.com"
    _used_emails.add(email)
    return email


_used_phones = set()


def random_phone():
    """A made-up Singapore number. Phone numbers must be unique, so never repeat one."""
    while True:
        phone = f"+65 {random.choice('89')}{random.randint(0, 9999999):07d}"
        if phone not in _used_phones:
            _used_phones.add(phone)
            return phone


app = create_app()

with app.app_context():
    db.drop_all()
    db.create_all()
    IDPCategory.ensure_defaults()   # PM-04 category list
    UserProfile.ensure_defaults()   # UA-09 profile list

    # One known account per role for demos (password: password123)
    for role in UserAccount.ROLES:
        UserAccount.create(f"{role}@demo.com", "password123", role,
                           name=f"Demo {role.title()}", phone=random_phone())

    for role in ("customer", "designer"):
        for _ in range(100):
            name = random_name()
            UserAccount.create(email_for(name), "password123", role,
                               name=name, phone=random_phone())

    # 100 designer applications: 60 pending, 25 approved, 15 rejected
    admin = UserAccount.query.filter_by(email="admin@demo.com").first()
    password_hash = generate_password_hash("password123")  # hash once, it's slow
    applications = []
    for _ in range(100):
        company = " ".join(random.sample(COMPANY_WORDS, 2) + [random.choice(COMPANY_TYPES)])
        name = random_name()
        application = DesignerApplication(
            name=name, email=email_for(name), phone=random_phone(),
            password_hash=password_hash, company_name=company,
            uen=f"20{random.randint(10, 25)}{random.randint(10000, 99999)}"
                f"{random.choice('ABCDEFGHKMNRWZ')}",
            portfolio_url=f"https://{company.lower().replace(' ', '')}.sg",
            experience_years=random.randint(1, 20),
            description=f"{company} is a small team designing {random.choice(STYLES).lower()} homes "
                        f"for HDB and condo owners. Every project is led by one designer from "
                        f"first meeting to handover.",
            submitted_at=datetime.now() - timedelta(days=random.randint(0, 60),
                                                    minutes=random.randint(0, 1439)),
        )
        db.session.add(application)
        applications.append(application)
    db.session.commit()

    approved_designers = []
    for application in applications[60:85]:
        approved_designers.append(application.approve(admin.id))
        # Spread "verified since" years so profiles look realistic
        application.reviewed_at = datetime(random.randint(2015, 2025), random.randint(1, 12), 1)
    for application in applications[85:]:
        application.reject(admin.id, "Could not verify company UEN.")
    db.session.commit()

    # 100 IDPs, owned by the approved designers (they have company profiles)
    idps = []
    for _ in range(100):
        style, place, category = random.choice(STYLES), random.choice(PLACES), random.choice(IDP.CATEGORIES)
        room = "makeover" if category == "Whole Home" else category.lower()
        idp = IDP(
            title=f"{style} {place} {room}",
            description=f"A {style.lower()} {room} for a {place} home.",
            category=category,
            designer_id=random.choice(approved_designers).id,
            view_count=random.randint(0, 5000),
            shortlist_count=random.randint(0, 300),
            is_current=random.random() < 0.25,
            created_at=datetime.now() - timedelta(days=random.randint(0, 700)),
        )
        db.session.add(idp)
        idps.append(idp)
    db.session.commit()

    # The demo customer starts with 6 favourites
    demo_customer = UserAccount.query.filter_by(email="customer@demo.com").first()
    for idp in random.sample(idps, 6):
        Favourite.add(demo_customer.id, idp)

    customers = UserAccount.query.filter_by(role="customer").all()

    # Platform reports (PM-08 to PM-10) need activity spread over time:
    # account "date created" over the last 90 days ...
    for account in UserAccount.query.filter(~UserAccount.email.like("%@demo.com")):
        account.created_at = datetime.now() - timedelta(days=random.randint(0, 90),
                                                        minutes=random.randint(0, 1439))
    # ... 3,000 logged IDP views over the last 60 days, favouring popular projects ...
    for idp in random.choices(idps, weights=[i.view_count + 1 for i in idps], k=3000):
        db.session.add(IDPView(idp_id=idp.id, category=idp.category, viewed_at=datetime.now() - timedelta(
            days=random.randint(0, 60), minutes=random.randint(0, 1439))))
    # ... and 120 customer shortlists over the last 60 days
    for customer in random.sample(customers, 40):
        for idp in random.sample(idps, 3):
            if Favourite.add(customer.id, idp):
                Favourite.find(customer.id, idp.id).saved_at = datetime.now() - timedelta(
                    days=random.randint(0, 60), minutes=random.randint(0, 1439))

    # 5 suspended customers for the UA-06 / UA-13 demos (never the demo login)
    for account in random.sample([c for c in customers if c.email != "customer@demo.com"], 5):
        account.is_suspended = True

    # UA-18 announcements
    for days_ago, title, message in [
        (20, "Welcome to Nestfolio", "Browse projects, save your favourites and contact designers directly."),
        (6, "Scheduled maintenance", "Nestfolio will be down on Sunday from 2am to 4am."),
        (1, "New: download reports", "Platform reports can now be downloaded as PDF or CSV."),
    ]:
        db.session.add(Announcement(admin_id=admin.id, title=title, message=message,
                                    sent_at=datetime.now() - timedelta(days=days_ago)))

    # 100 reports for the User Admin's review list (C-15 / UA-17): 70 open, 30 resolved.
    # Each customer reports each project at most once.
    pairs = random.sample([(c, i) for c in customers for i in idps], 100)
    for n, (customer, idp) in enumerate(pairs):
        report = Report(customer_id=customer.id, idp_id=idp.id,
                        reason=random.choice(Report.REASONS),
                        details=random.choice(["", "Photos look like they are from another website.",
                                               "The description is just an advert.",
                                               "Price and details seem wrong."]),
                        created_at=datetime.now() - timedelta(days=random.randint(0, 30),
                                                              minutes=random.randint(0, 1439)))
        if n >= 70:
            report.status, report.resolved_by = "resolved", admin.id
            report.resolved_at = report.created_at + timedelta(days=1)
        db.session.add(report)

    # 100 enquiries for designers' enquiry lists (C-16 / ID-21);
    # the demo designer gets 8 so the page has something to show
    demo_designer = UserAccount.query.filter_by(email="designer@demo.com").first()
    messages = ["Hi, I like this design. Could you give me a quote for my flat?",
                "Are you available to start in two months? It's a 4-room HDB.",
                "What is your usual budget range for a whole-home renovation?",
                "Could we arrange a site visit next week?"]
    for n in range(100):
        customer = random.choice(customers)
        if n < 8:
            designer_id, idp_id = demo_designer.id, None
        else:
            idp = random.choice(idps)
            designer_id, idp_id = idp.designer_id, idp.id
        db.session.add(Enquiry(
            designer_id=designer_id, customer_id=customer.id, idp_id=idp_id,
            name=customer.name, contact=customer.email, message=random.choice(messages),
            created_at=datetime.now() - timedelta(days=random.randint(0, 30),
                                                  minutes=random.randint(0, 1439))))
    db.session.commit()

    print(f"Accounts: {UserAccount.query.count()}, IDPs: {IDP.query.count()}, "
          f"Favourites: {Favourite.query.count()}, "
          f"Reports: {Report.query.count()} ({Report.count_open()} open), "
          f"Enquiries: {Enquiry.query.count()}, IDP views logged: {IDPView.query.count()}, "
          f"Categories: {IDPCategory.query.count()}, Profiles: {UserProfile.query.count()}, "
          f"Announcements: {Announcement.query.count()}, "
          f"Designer applications: {DesignerApplication.query.count()} "
          f"({DesignerApplication.count_pending()} pending)")
    print("Demo logins: admin@demo.com / designer@demo.com / customer@demo.com / "
          "platform@demo.com  (password: password123)")
    print(f"Pending applicant example: {applications[0].email} (cannot log in until approved)")
