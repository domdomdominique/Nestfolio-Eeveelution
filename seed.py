"""Generate realistic demo data for Nestfolio (at least 100 records per data type).

Run:  python seed.py   (then start the site with: python run.py)

Everything is generated from a fixed random seed, so every run gives the same data.
Numbers shown on the site always match the records behind them: a project's view
count equals its logged views, and its shortlist count equals the customers who saved it.
"""
import os
import random
from datetime import datetime, timedelta

from io import BytesIO

from PIL import Image
from werkzeug.security import generate_password_hash

from app import create_app
from app.entity.announcement import Announcement
from app.entity.db import db
from app.entity.designer_application import DesignerApplication
from app.entity.designer_company import DesignerCompany
from app.entity.enquiry import Enquiry
from app.entity.reply import EnquirySeen, Reply
from app.entity.favourite import Favourite
from app.entity.idp import IDP
from app.entity.idp_category import IDPCategory, IDPCategoryPhoto
from app.entity.idp_photo import IDPPhoto
from app.entity.idp_view import IDPView
from app.entity.report import Report
from app.entity.user_account import UserAccount
from app.entity.user_profile import UserProfile

random.seed(314)  # same data every run, so demos are repeatable
NOW = datetime.now().replace(second=0, microsecond=0)
PASSWORD = "password123"

# --- People ---------------------------------------------------------------------------
CHINESE_GIVEN = ["Wei Ming", "Hui Min", "Jun Jie", "Xin Yi", "Jia Hui", "Zhi Hao", "Shu Ting", "Kai Wen",
                 "Li Ting", "Yong Sheng", "Mei Ling", "Jun Wei", "Pei Shan", "Jia Le", "Wen Xuan", "Zi Xuan"]
CHINESE_FAMILY = ["Tan", "Lim", "Lee", "Ng", "Wong", "Goh", "Ong", "Koh", "Teo", "Chua", "Chen", "Low",
                  "Yeo", "Sim", "Chong", "Tay"]
MALAY = ["Ahmad Faizal", "Nur Aisyah", "Muhammad Irfan", "Siti Nurhaliza", "Farhan Iskandar", "Nurul Huda",
         "Hafiz Rahman", "Aliyah Zainal", "Danish Hakim", "Syafiqah Osman"]
INDIAN = ["Rajesh Kumar", "Priya Nair", "Arjun Pillai", "Divya Menon", "Vikram Singh", "Kavitha Raj",
          "Suresh Ramasamy", "Anjali Krishnan", "Naveen Das", "Meera Iyer"]
OTHERS = ["Daniel Lim", "Rachel Goh", "Marcus Tan", "Chloe Ng", "Ethan Wong", "Grace Teo", "Ryan Koh",
          "Sarah Lee", "Nicholas Chua", "Hannah Ong", "Jonathan Yeo", "Amanda Sim"]


def random_name():
    r = random.random()
    if r < 0.55:
        return f"{random.choice(CHINESE_FAMILY)} {random.choice(CHINESE_GIVEN)}" if random.random() < 0.3 \
            else f"{random.choice(CHINESE_GIVEN)} {random.choice(CHINESE_FAMILY)}"
    if r < 0.7:
        return random.choice(MALAY)
    if r < 0.85:
        return random.choice(INDIAN)
    return random.choice(OTHERS)


_used_emails = set()


def email_for(name, domain="test.com"):
    """"Wei Ming Tan" -> weiming.tan@test.com; repeated names get a number."""
    parts = name.lower().split()
    base = f"{''.join(parts[:-1])}.{parts[-1]}" if len(parts) > 1 else parts[0]
    email, n = f"{base}@{domain}", 1
    while email in _used_emails:
        n += 1
        email = f"{base}{n}@{domain}"
    _used_emails.add(email)
    return email


_used_phones = set()


def random_phone(first_digits="89"):
    """A made-up Singapore number (mobile 8/9, office 6). Never repeats."""
    while True:
        phone = f"+65 {random.choice(first_digits)}{random.randint(0, 9999999):07d}"
        if phone not in _used_phones:
            _used_phones.add(phone)
            return phone


def ago(days_min, days_max, after=None):
    """A random time between days_max and days_min days ago, never before `after`."""
    moment = NOW - timedelta(days=random.uniform(days_min, days_max))
    if after and moment <= after:
        moment = after + timedelta(hours=random.uniform(1, 72))
    return min(moment, NOW)


# --- Companies --------------------------------------------------------------------------
COMPANY_FIRST = ["Oak & Ash", "Nest", "Haus", "Atelier Linea", "Terra", "Mosaic", "Ember", "Blanc", "Zen",
                 "Kinfolk", "Arc", "Sora", "Fable", "Willow", "Copper", "Marble & Moss", "Ivory", "Lumen",
                 "Northlight", "Harbour", "Cedar", "Pebble", "Tide", "Juniper", "Monolith"]
COMPANY_LAST = ["Interiors", "Design Studio", "Living", "Concepts", "Spaces", "Interior Design", "Studio",
                "Homes", "Design Co.", "Atelier"]
STREETS = [("Ubi Avenue 1", "408934"), ("Kaki Bukit Road 1", "415934"), ("Tai Seng Street", "534057"),
           ("Changi Business Park Crescent", "486065"), ("Upper Paya Lebar Road", "534818"),
           ("Jalan Besar", "208792"), ("Tanjong Pagar Road", "088443"), ("Kallang Avenue", "339411"),
           ("Bukit Batok Crescent", "658065"), ("Woodlands Industrial Park E1", "757741"),
           ("Toa Payoh Lorong 8", "319254"), ("Ang Mo Kio Industrial Park 2", "569500"),
           ("Geylang Bahru", "339631"), ("Eunos Avenue 7", "409571"), ("Alexandra Road", "159961")]
SPECIALITIES = ["warm, practical HDB renovations", "condo makeovers that make small spaces feel bigger",
                "Japandi and Scandinavian homes with lots of natural light", "landed homes and full rebuilds",
                "kitchens and bathrooms", "minimalist homes with hidden storage",
                "family homes designed around children and pets", "industrial lofts and shophouse conversions"]


def make_company(used):
    while True:
        name = f"{random.choice(COMPANY_FIRST)} {random.choice(COMPANY_LAST)}"
        if name not in used:
            used.add(name)
            return name


def company_slug(name):
    return "".join(ch for ch in name.lower() if ch.isalnum())


def random_uen(year):
    """Singapore company UEN format: YYYYNNNNNX (e.g. 201912345K)."""
    return f"{year}{random.randint(10000, 99999)}{random.choice('ABCDEGHKMNRWZ')}"


def company_address():
    street, postal = random.choice(STREETS)
    return f"{random.randint(1, 80)} {street}, #{random.randint(1, 12):02d}-{random.randint(1, 40):02d}, Singapore {postal}"


def company_description(name, speciality, years, team):
    return (f"{name} is a team of {team} designers specialising in {speciality}. "
            f"Over {years} years we have completed homes across Singapore, from first sketch to handover. "
            f"Every project has one lead designer, a fixed quotation and a dedicated project manager on site.")


# --- Projects ----------------------------------------------------------------------------
STYLES = ["Scandinavian", "Japandi", "Modern Minimalist", "Industrial", "Contemporary", "Mid-Century Modern",
          "Modern Luxe", "Tropical", "Wabi-Sabi", "Classic", "Muji-inspired"]
HOMES = [("4-room HDB", "Punggol", 990), ("5-room HDB", "Sengkang", 1180), ("3-room HDB", "Toa Payoh", 700),
         ("4-room BTO", "Tengah", 970), ("5-room BTO", "Bidadari", 1140), ("executive maisonette", "Tampines", 1560),
         ("3-bedroom condo", "Bukit Timah", 1250), ("2-bedroom condo", "Novena", 750),
         ("penthouse", "River Valley", 2400), ("terrace house", "Serangoon Gardens", 2900),
         ("semi-detached house", "Upper Thomson", 3400), ("shophouse", "Joo Chiat", 2100),
         ("4-room resale HDB", "Clementi", 1000), ("1-bedroom condo", "Tiong Bahru", 520),
         ("3-room resale HDB", "Ang Mo Kio", 680)]
ROOM_WORD = {"Living Room": "living room", "Kitchen": "kitchen", "Bedroom": "master bedroom",
             "Bathroom": "bathroom", "Study & Office": "study", "Whole Home": "home"}
FEATURES = {
    "Living Room": ["a built-in TV console with concealed wiring", "a feature wall in fluted panels",
                    "cove lighting that changes from warm to bright", "an L-shaped sofa nook by the window",
                    "full-height storage hiding the DB box and shoe cabinet", "a vinyl floor in light oak"],
    "Kitchen": ["a quartz island with seating for four", "soft-close cabinets up to the ceiling",
                "an open-concept layout joined to the dining area", "a sintered stone backsplash",
                "a hidden appliance tower", "under-cabinet LED strips"],
    "Bedroom": ["a platform bed with drawers underneath", "a walk-in wardrobe with glass doors",
                "blackout curtains on a ceiling track", "a headboard wall in soft upholstery",
                "a compact vanity corner", "warm 2700K lighting on dimmers"],
    "Bathroom": ["a walk-in shower with a frameless screen", "large-format porcelain tiles",
                 "a floating vanity with an LED mirror", "a niche for toiletries in the shower wall",
                 "matte black fittings", "a rain shower with a hand-held set"],
    "Study & Office": ["a built-in desk along the window", "floor-to-ceiling bookshelves",
                       "acoustic panels for video calls", "a pull-out guest bed hidden in the carpentry",
                       "cable trays under the desk", "a reading chair corner"],
    "Whole Home": ["hacking two walls to open up the kitchen", "a consistent oak and white palette",
                   "smart lighting in every room", "re-wiring and new plumbing throughout",
                   "built-in storage in every room", "a new layout for a family of four"],
}
BRIEFS = ["The owners wanted", "Our clients, a young couple, asked for", "The family needed",
          "The homeowner, who works from home, wanted", "Our clients, recently retired, asked for"]
GOALS = ["more storage without losing space", "a calm space that is easy to clean",
         "room for their two children to play", "a home that feels brighter and bigger",
         "a place to host friends on weekends", "a design that would age well"]


def project_details(category):
    style = random.choice(STYLES)
    home, town, sqft = random.choice(HOMES)
    room = ROOM_WORD[category]
    title = f"{style} {room} for a {home} in {town}" if category != "Whole Home" else \
        f"{style} {home} in {town}"
    weeks = random.randint(3, 8) if category != "Whole Home" else random.randint(8, 14)
    budget = random.randint(8, 30) * 1000 if category != "Whole Home" else random.randint(45, 160) * 1000
    feats = random.sample(FEATURES[category], 3)
    description = (f"{random.choice(BRIEFS)} {random.choice(GOALS)}. We designed this {style.lower()} {room} "
                   f"around {feats[0]}, {feats[1]} and {feats[2]}. "
                   f"Home size: about {sqft} sq ft. Completed in {weeks} weeks, "
                   f"budget around S${budget:,}.")
    return title[:150], description


# --- Messages -----------------------------------------------------------------------------
ENQUIRY_MESSAGES = [
    "Hi, I like this design. Could you give me a rough quote for a similar look in my {home}?",
    "We just collected the keys to our {home} in {town}. Are you available to start in about two months?",
    "What is your usual budget range for a whole-home renovation of a {home}?",
    "Could we arrange a site visit next week? I'm free on weekday evenings and Saturday mornings.",
    "Love the storage ideas here. Do you also handle electrical and plumbing works?",
    "Hi! Our budget is around S${budget}k. Is that realistic for the kitchen and two bathrooms?",
    "Do you offer 3D drawings before we confirm the design?",
    "How long would a project like this take for a {home}? We need to move in by {month}.",
]
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
          "October", "November", "December"]
REPORT_DETAILS = {
    "Spam or advertising": ["The description is just an advert for furniture.", "Contains a promo code.", ""],
    "Wrong or misleading information": ["The budget shown is far too low for this work.",
                                        "This is a condo, not an HDB flat.", ""],
    "Inappropriate photos or content": ["One of the photos is not related to the project.", ""],
    "Copied from another designer": ["I saw the same photos on another company's Instagram.",
                                     "These photos are from a magazine.", ""],
    "Other": ["The designer did not reply to my enquiry for a month.", "Duplicate of another project.", ""],
}

# --- Demo photos -----------------------------------------------------------------------------
# Every project gets a random photo from app/static/img/idpbg and every category a random background
# from app/static/img/idpcatbg. The source images are large wallpapers, so each one is scaled down
# and saved as a JPEG that fits the normal upload rules (ID-19: JPG/PNG, 5 MB, 20 megapixels).
IMG_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app", "static", "img")
PHOTO_MAX_SIDE = 1600  # long edge in pixels: sharp on the site, small in the database


def images_in(folder):
    folder = os.path.join(IMG_FOLDER, folder)
    if not os.path.isdir(folder):
        return []
    return sorted(os.path.join(folder, f) for f in os.listdir(folder)
                  if f.lower().endswith((".jpg", ".jpeg", ".png")))


def load_photo(path):
    """The image at path as a downscaled JPEG, ready to store as a photo record."""
    with Image.open(path) as image:
        image.draft("RGB", (PHOTO_MAX_SIDE, PHOTO_MAX_SIDE))  # JPEGs decode straight at a smaller size
        if image.mode == "P":
            image = image.convert("RGBA")  # palette PNGs with transparency must go through RGBA first
        image = image.convert("RGB")
        image.thumbnail((PHOTO_MAX_SIDE, PHOTO_MAX_SIDE), Image.LANCZOS)
        out = BytesIO()
        image.save(out, "JPEG", quality=82, optimize=True, progressive=True)
    name = os.path.splitext(os.path.basename(path))[0][:250] + ".jpg"
    return {"filename": name, "content_type": "image/jpeg", "data": out.getvalue()}


def assign_photos(items, folder, attach):
    """Attach a random image from folder to each item; returns how many items got one.

    Images are dealt like shuffled cards, so none repeats until every one has been used,
    and each image is only decoded once.
    """
    sources = images_in(folder)
    if not sources:
        print(f"No images in app/static/img/{folder}, so those records have no photos.")
        return 0
    cache, deck = {}, []
    for item in items:
        if not deck:
            deck = random.sample(sources, len(sources))
        path = deck.pop()
        if path not in cache:
            cache[path] = load_photo(path)
        attach(item, cache[path])
    db.session.commit()
    return len(items)


def attach_category_photo(category, photo):
    category.photo = IDPCategoryPhoto(**photo)


# seed.py rebuilds everything, so remove the old database first. This also avoids the
# "encryption_key.key is missing but eeveelution.db exists" error after pulling new code.
OLD_DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "instance", "eeveelution.db")
if os.path.exists(OLD_DATABASE):
    os.remove(OLD_DATABASE)

app = create_app()

with app.app_context():
    db.drop_all()
    db.create_all()
    IDPCategory.ensure_defaults()   # PM-04 category list
    UserProfile.ensure_defaults()   # UA-09 profile list
    categories = IDPCategory.names()
    password_hash = generate_password_hash(PASSWORD)  # hash once, it's slow

    # --- Staff and demo logins -------------------------------------------------------------
    admin = UserAccount.create("admin@demo.com", PASSWORD, "admin", name="Demo Admin", phone=random_phone())
    UserAccount.create("platform@demo.com", PASSWORD, "platform", name="Demo Platform", phone=random_phone())
    for account in UserAccount.query.all():
        account.created_at = NOW - timedelta(days=400)

    # --- 100 customers (plus the demo customer) ----------------------------------------------
    customers = [UserAccount.create("customer@demo.com", PASSWORD, "customer", name="Demo Customer",
                                    phone=random_phone())]
    customers[0].created_at = NOW - timedelta(days=200)
    for _ in range(100):
        name = random_name()
        account = UserAccount(email=email_for(name), role="customer", name=name, phone=random_phone(),
                              password_hash=password_hash, created_at=ago(0, 365))
        db.session.add(account)
        customers.append(account)
    db.session.commit()

    # --- Designer applications: 100 approved (with companies), 40 pending, 15 rejected -------
    used_companies = set()

    def new_application(name, email, submitted, years=None):
        company = make_company(used_companies)
        years = years or random.randint(2, 22)
        speciality = random.choice(SPECIALITIES)
        application = DesignerApplication(
            name=name, email=email, phone=random_phone(), password_hash=password_hash,
            company_name=company, uen=random_uen(min(2025, NOW.year - years + random.randint(0, 2))),
            portfolio_url=f"https://www.{company_slug(company)}.sg", experience_years=years,
            description=company_description(company, speciality, years, random.randint(3, 25)),
            submitted_at=submitted)
        db.session.add(application)
        return application

    approved = [new_application("Demo Designer", "designer@demo.com", NOW - timedelta(days=380), years=8)]
    for _ in range(99):
        name = random_name()
        approved.append(new_application(name, email_for(name), ago(30, 900)))
    pending = []
    for _ in range(40):
        name = random_name()
        pending.append(new_application(name, email_for(name), ago(0, 21)))
    rejected = []
    for _ in range(15):
        name = random_name()
        rejected.append(new_application(name, email_for(name), ago(10, 120)))
    db.session.commit()

    designers = []
    for application in approved:
        account = application.approve(admin.id)
        application.reviewed_at = application.submitted_at + timedelta(days=random.uniform(1, 5))
        account.created_at = application.reviewed_at
        # The company record designers manage on their Company page (ID-03 to ID-05)
        company_email = f"hello@{company_slug(application.company_name)}.sg"
        db.session.add(DesignerCompany(
            account_id=account.id, company_name=application.company_name,
            description=application.description, address=company_address(),
            phone=random_phone("6"), email=company_email, uen=application.uen,
            portfolio_url=application.portfolio_url, experience_years=application.experience_years,
            reviewed_at=application.reviewed_at))
        designers.append(account)
    reasons = ["Could not verify the company UEN with ACRA.", "Portfolio link does not work.",
               "The company is not registered as an interior design business.",
               "Duplicate application for a company already on Nestfolio."]
    for application in rejected:
        application.reject(admin.id, random.choice(reasons))
        application.reviewed_at = application.submitted_at + timedelta(days=random.uniform(1, 7))
    db.session.commit()

    # --- About 250 projects: every designer has 1-5, the demo designer has 6 ------------------------
    idps = []
    for i, designer in enumerate(designers):
        count = 6 if i == 0 else random.choices([1, 2, 3, 4, 5], weights=[2, 4, 4, 2, 1])[0]
        for _ in range(count):
            category = random.choice(categories)
            title, description = project_details(category)
            created = ago(0, 600, after=designer.created_at)
            idp = IDP(title=title, description=description, category=category, designer_id=designer.id,
                      is_current=(NOW - created).days < 90 and random.random() < 0.6,
                      created_at=created, view_count=0, shortlist_count=0)
            db.session.add(idp)
            idps.append(idp)
    db.session.commit()

    # --- Views: logged one by one, so counts, statistics and reports always agree -------------
    popularity = {idp.id: random.paretovariate(1.6) for idp in idps}
    views = []
    for idp in idps:
        age_days = max((NOW - idp.created_at).days, 1)
        n = int(min(popularity[idp.id] * 25 * min(age_days, 120) / 120, 600))
        for _ in range(n):
            views.append(IDPView(idp_id=idp.id, category=idp.category,
                                 viewed_at=ago(0, min(age_days, 180), after=idp.created_at)))
        idp.view_count = n
    db.session.bulk_save_objects(views)
    db.session.commit()

    # --- Favourites (shortlists): each customer saves 2-9 projects, popular ones more often ---
    weights = [popularity[i.id] for i in idps]
    for customer in customers:
        picks = list(dict.fromkeys(random.choices(idps, weights=weights, k=random.randint(2, 9))))
        for idp in picks:
            db.session.add(Favourite(customer_id=customer.id, idp_id=idp.id,
                                     saved_at=ago(0, 180, after=max(customer.created_at, idp.created_at))))
            idp.shortlist_count += 1
    db.session.commit()

    # --- 5 suspended customers for the UA-06 / UA-13 demos --------------------------------------
    for account in random.sample(customers[1:], 5):
        account.is_suspended = True

    # --- 250 enquiries (C-16 / ID-21); the demo designer gets 10 about their projects ----------
    demo_projects = [i for i in idps if i.designer_id == designers[0].id]
    for n in range(250):
        customer = random.choice(customers)
        idp = random.choice(demo_projects) if n < 10 else random.choice(idps + [None] * 20)
        designer_id = idp.designer_id if idp else random.choice(designers).id
        home, town, _ = random.choice(HOMES)
        message = random.choice(ENQUIRY_MESSAGES).format(
            home=home, town=town, budget=random.randint(4, 12) * 10, month=random.choice(MONTHS))
        contact = customer.email if random.random() < 0.7 else customer.phone
        db.session.add(Enquiry(
            designer_id=designer_id, customer_id=customer.id, idp_id=idp.id if idp else None,
            name=customer.name, contact=contact, message=message,
            created_at=ago(0, 60, after=idp.created_at if idp else None)))

    # The demo customer has sent 3 enquiries of their own
    for idp in random.sample(idps, 3):
        db.session.add(Enquiry(designer_id=idp.designer_id, customer_id=customers[0].id, idp_id=idp.id,
                               name=customers[0].name, contact=customers[0].email,
                               message="Hi, I love this project. Could you give me a rough quote for my 4-room HDB?",
                               created_at=ago(2, 10, after=idp.created_at)))
    db.session.commit()

    # --- Replies (ID-21): designers answer most enquiries; some customers write back ----------
    DESIGNER_REPLIES = [
        "Thanks for reaching out! A similar design usually starts from about S${k}k. Shall we arrange a site visit?",
        "Hi {name}, yes we are available. Could you share your floor plan so we can prepare a quote?",
        "Thank you! We can start in about {weeks} weeks. Would a call this Saturday work for you?",
        "Hi {name}, happy to help. Our 3D drawings are included once you confirm the design.",
    ]
    CUSTOMER_REPLIES = ["Great, Saturday morning works for me.", "Sure, I'll email the floor plan tonight.",
                        "Thanks! Could you also include the bathrooms in the quote?"]
    for enquiry in Enquiry.query.all():
        demo = enquiry.customer_id == customers[0].id
        if random.random() < 0.55 or demo:
            replied = min(enquiry.created_at + timedelta(hours=random.uniform(2, 48)), NOW)
            db.session.add(Reply(enquiry_id=enquiry.id, sender_id=enquiry.designer_id, created_at=replied,
                                 message=random.choice(DESIGNER_REPLIES).format(
                                     k=random.randint(3, 9) * 10, weeks=random.randint(2, 8),
                                     name=enquiry.name.split()[0])))
            # The designer saw the enquiry when replying; older replies were read by the customer
            db.session.add(EnquirySeen(enquiry_id=enquiry.id, user_id=enquiry.designer_id, seen_at=replied))
            if (NOW - replied).days >= 2 and not demo:
                db.session.add(EnquirySeen(enquiry_id=enquiry.id, user_id=enquiry.customer_id, seen_at=NOW))
                if random.random() < 0.3:
                    db.session.add(Reply(enquiry_id=enquiry.id, sender_id=enquiry.customer_id,
                                         message=random.choice(CUSTOMER_REPLIES),
                                         created_at=min(replied + timedelta(hours=random.uniform(1, 24)), NOW)))
    db.session.commit()

    # --- 100 reports (C-15 / UA-17): 70 open, 30 resolved; each customer reports a project once -
    pairs = random.sample([(c, i) for c in customers[1:] for i in idps], 100)
    for n, (customer, idp) in enumerate(pairs):
        reason = random.choice(Report.REASONS)
        report = Report(customer_id=customer.id, idp_id=idp.id, reason=reason,
                        details=random.choice(REPORT_DETAILS.get(reason, [""])),
                        created_at=ago(0, 30, after=idp.created_at))
        if n >= 70:
            report.status, report.resolved_by, report.resolution = "resolved", admin.id, "dismissed"
            report.resolved_at = report.created_at + timedelta(days=random.uniform(0.5, 3))
        db.session.add(report)

    # --- UA-18 announcements --------------------------------------------------------------------
    for days_ago, title, message in [
        (45, "Welcome to Nestfolio", "Browse real projects from verified Singapore interior designers, "
                                     "save your favourites and contact designers directly."),
        (20, "New categories coming", "Platform Management will be reviewing project categories this month. "
                                      "Designers, please check your projects are in the right category."),
        (6, "Scheduled maintenance", "Nestfolio will be unavailable on Sunday from 2am to 4am for upgrades."),
        (1, "New: download reports", "Platform reports can now be downloaded as PDF or CSV."),
    ]:
        db.session.add(Announcement(admin_id=admin.id, title=title, message=message,
                                    sent_at=NOW - timedelta(days=days_ago)))
    db.session.commit()

    # --- Photos for every project and category -----------------------------------------------
    print("Adding demo photos (this can take a minute)...")
    project_photos = assign_photos(IDP.query.order_by(IDP.id).all(), "idpbg",
                                   lambda p, photo: p.photos.append(IDPPhoto(**photo)))
    category_photos = assign_photos(IDPCategory.query.order_by(IDPCategory.id).all(), "idpcatbg",
                                    attach_category_photo)

    print(f"Accounts: {UserAccount.query.count()} ({len(customers)} customers, {len(designers)} designers), "
          f"companies: {DesignerCompany.query.count()}, projects: {IDP.query.count()}, "
          f"views logged: {IDPView.query.count()}, favourites: {Favourite.query.count()}, "
          f"enquiries: {Enquiry.query.count()} ({Reply.query.count()} replies), reports: {Report.query.count()} ({Report.count_open()} open), "
          f"applications: {DesignerApplication.query.count()} ({DesignerApplication.count_pending()} pending), "
          f"categories: {IDPCategory.query.count()}, profiles: {UserProfile.query.count()}, "
          f"announcements: {Announcement.query.count()}, "
          f"photos: {project_photos} projects, {category_photos} categories")
    print(f"Demo logins (password: {PASSWORD}): admin@demo.com / platform@demo.com / "
          f"designer@demo.com / customer@demo.com")
    print(f"Pending applicant example: {pending[0].email}")
    print("Done. Start the site with: python run.py")
