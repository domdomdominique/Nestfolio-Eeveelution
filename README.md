# Nestfolio — CSIT314 Group Project (Team Eeveelution)

[![CI](https://github.com/domdomdominique/Nestfolio-Eeveelution/actions/workflows/ci.yml/badge.svg)](https://github.com/domdomdominique/Nestfolio-Eeveelution/actions/workflows/ci.yml)

**Nestfolio** is an online platform that matches renovation customers with interior designers. Customers browse, save and enquire about Interior Design Projects (IDPs), and chat with designers. Designers publish a portfolio and track how it performs. Platform Management curates categories and reports on activity, and User Admins keep accounts and content in order.

Built for **CSIT314 Software Development Methodologies** (UOW, SIM S4 2026) with Python and Flask. The code follows the **Boundary–Control–Entity (B-C-E)** design, and the team works in Scrum with test-driven development and continuous integration.

**Status:** all 67 user stories across the four actors are built, and every acceptance criterion has a passing test.

----

## Team Eeveelution

| Member     | Role                        |
|------------|-----------------------------|
| Jeremiah   | Backend programmer          |
| Dominique  | Project Manager, Documenter |
| Bryan      | Frontend programmer         |
| Thiri      | Designer                    |
| Bingxuan   | Designer                    |
| Xi Ze      | Backend programmer          |

---

## Features

Story IDs (C-, ID-, PM-, UA-) refer to the team's user story sheet.

### Customer (C-01 to C-17)
- Register, log in and log out. Logging out returns to the login page, and logged-in pages are not cached.
- View and update their profile (name, email, phone, date joined). Changing details requires the current password, and passwords can be changed.
- Browse IDPs with keyword search, category filters, a current/past status filter, and sorting by **Recommended**, **Most viewed** or **Newest**.
- View an IDP's details and photo gallery. Each view is logged anonymously.
- Save IDPs to favourites, then search, sort and remove them.
- Browse designers and view a designer's public profile (company photo, cover image and portfolio).
- **Send an enquiry** to a designer, optionally attaching up to 5 photos (JPG/PNG) or PDFs (5 MB each).
- **My enquiries:** a two-pane inbox showing each conversation with a designer. Customers see the designer's replies and can answer back, and new replies show an unread badge.
- Report an inappropriate IDP (once per project).
- See announcements meant for them on the home page.

### Interior Designer (ID-01 to ID-21)
- Apply to join with company details (company name, UEN, portfolio URL, years of experience).
- Check application status (pending, or rejected with a reason). A pending or rejected applicant who logs in with the right password sees their status instead of the dashboard.
- Add, view, edit and delete their **company profile**, with a profile picture and cover image (5 MB each).
- Manage a **portfolio**: add, edit and delete IDPs with up to 10 JPG/PNG photos each (10 MB per photo), mark projects current or past, and search their own portfolio.
- **Statistics:** view and shortlist counts for each IDP, plus an over-time chart of views and shortlists.
- **Trends:** the platform's most viewed categories and IDPs over the last 7 or 30 days, with a chart.
- **Enquiries inbox:** All / Unread / Replied tabs, search, and unread badges. Designers reply to customers, with optional photo or PDF attachments.
- When a User Admin removes one of their projects, a personal notice with the reason appears on their dashboard, and the project is marked "Project Removed" in their portfolio.
- View and edit their own account details.

### Platform Management (PM-01 to PM-11)
- Create, view, search, update and delete **IDP categories**. Each category needs a background photo, which is shown on the landing page. A category's page lists the IDPs filed under it, with search and paging.
- Generate **daily, weekly (Monday to Sunday) and monthly activity reports**: new accounts, new IDPs, total views and shortlists, the top IDPs and categories by views and by shortlists, and a views/shortlists chart.
- **Download** any report as PDF or Excel. The Excel workbook has Summary, Activity and Top lists sheets, each with native Excel charts. Text cells are stored as text, which protects them against formula injection.

### User Admin (UA-01 to UA-18)
- **Dashboard charts:** new accounts, designer applications, projects reported and reports resolved per day, compared with the previous period.
- Create, view, search and update **user accounts**, and suspend or reactivate them.
- **Reset a user's password**: a one-time temporary password is generated, and the user must change it at their next login.
- Create, view, search, update and suspend **user profiles** (roles). Suspending a profile blocks every account in it.
- Review **designer applications** and approve or reject them, with a reason.
- Review **reported IDPs**: dismiss the report, or remove the project with a reason that is sent to the designer.
- Send and remove **announcements**, either to everyone or only to selected roles.

---

## Tech stack

| Area       | Technology |
|------------|------------|
| Language   | Python 3.12 |
| Web        | Flask 3.1, Jinja templates, Pico CSS, server-drawn SVG charts (no JavaScript chart library) |
| Database   | SQLite via Flask-SQLAlchemy (WAL mode) |
| Forms      | Flask-WTF (CSRF protection) |
| Images     | Pillow (upload validation and resizing) |
| Reports    | openpyxl (Excel), small built-in PDF writer |
| Security   | Werkzeug password hashing, Fernet field encryption (`cryptography`) |
| Testing    | pytest |
| CI         | GitHub Actions |
| Deployment | Gunicorn |

---

## Getting started

### 1. Clone the repository

```bash
git clone https://github.com/domdomdominique/Nestfolio-Eeveelution.git
cd Nestfolio-Eeveelution
```

### 2. Create a virtual environment and install dependencies

**Windows (PowerShell)**
```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

**macOS / Linux / Git Bash / Codespaces**
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Generate the demo data

```bash
python seed.py
```

This **deletes and rebuilds** the database with realistic Singapore demo data. It uses a fixed random seed, so every run gives the same data. The numbers on the site always match the records behind them: a project's view count equals its logged views, and its shortlist count equals the customers who saved it.

| Data | Records |
|------|---------|
| User accounts | 203: 101 customers (incl. demo, 5 suspended), 100 designers, 1 User Admin, 1 Platform Management |
| Designer applications | 155 (100 approved, 40 pending, 15 rejected) |
| Designer companies | 100, each with a profile picture and cover image |
| Interior Design Projects | 274 (1–5 per designer) with 2,740 photos |
| Logged IDP views | 13,853 |
| Favourites | 522 |
| Enquiries | 253, with 181 replies |
| Reported IDPs | 100 (70 open, 30 resolved) |
| Categories / user profiles | 6 / 4 defaults |
| Announcements | 4 |

Each project gets up to 10 photos from `app/static/img/idpbg`, each company a profile picture (`idpfp`) and cover (`idpbg`), and each category its background from `idpcatbg`. Photos are scaled down to fit the normal upload rules and stored in the database.

### 4. Run the app

```bash
python run.py
```

Open <http://127.0.0.1:5000>. To turn on the Flask debugger for local work only, run `FLASK_DEBUG=1 python run.py`.

Days, "today" and report periods use Singapore time whatever the server's own clock says (cloud hosts usually run UTC). Set `APP_TIMEZONE` (for example `APP_TIMEZONE=UTC`) to change it. On Windows, the PC's own time zone setting applies.

### Demo logins

All demo and generated accounts use the password `password123`.

| Role | Email |
|------|-------|
| User Admin | `admin@demo.com` |
| Interior Designer | `designer@demo.com` |
| Customer | `customer@demo.com` |
| Platform Management | `platform@demo.com` |

The demo designer has 6 projects and 10 enquiries. The demo customer has favourites and 3 enquiries of their own, so every page has something to show. Generated accounts use the person's full name run together, e.g. `weimingkoh@test.com`, with a number added for repeated names. `seed.py` prints a pending applicant at the end: log in with that email to see the registration status card.

### Upgrading an existing database

There is no migration tool. Normally you just run `python seed.py` again (it removes the old database first). Some newer columns, such as report removal reasons and reply attachments, are added to an older database automatically at start-up. If a database from before the phone-uniqueness checks needs to keep its records, run:

```bash
python upgrade_phone_hashes.py
```

It adds the phone fingerprint column without deleting anything, and stops if two accounts share a phone number.

---

## Testing

```bash
pytest -v
```

The suite has **496 tests** in 42 test files, and all of them pass. Tests run against an in-memory SQLite database with throwaway keys, so they never touch your local data.

### Acceptance tests by user story

Every acceptance criterion in the user story sheet (67 stories) is checked by a page-level test. The comment beside each assertion names the criterion it covers (e.g. `# C-03 AC3`).

| Area | Stories | Acceptance tests | Supporting tests |
|------|---------|------------------|------------------|
| Customer | C-01 to C-17 | `test_acceptance_customer.py` | `test_register`, `test_login`, `test_customer_pages`, `test_favourites`, `test_search_idp`, `test_landing_page`, `test_designer_profile*` |
| Interior Designer | ID-01 to ID-21 | `test_acceptance_designer.py`, `test_role_flows.py` | `test_designer_portfolio`, `test_designer_application`, `test_designer_profile_page`, `test_view_enquiries`, `test_enquiry_replies`, `test_designer_frontend` |
| Platform Management | PM-01 to PM-11 | `test_acceptance_platform_admin.py` | `test_idp_categories`, `test_platform_reports`, `test_platform_frontend`, `test_charts` |
| User Admin | UA-01 to UA-18 | `test_acceptance_platform_admin.py` | `test_user_accounts_admin`, `test_user_profiles`, `test_reset_password`, `test_review_reports*`, `test_announcements`, `test_admin_activity`, `test_admin_frontend` |
| Security, ethics and robustness | — | `test_security.py`, `test_ethics.py` | `test_session_validation`, `test_phone_encryption`, `test_unique_phone`, `test_phone_and_email_input`, `test_code_review_fixes` |
| Review feedback | — | `test_feedback_changes.py`, `test_idp_photo_category_and_removal_notice.py` | Role-targeted announcements, attachments, category backgrounds, removal notices |

The full mapping is in [`docs/test-coverage.md`](docs/test-coverage.md).

### Design decisions worth knowing

| Story | Decision |
|-------|----------|
| ID-01 AC5, ID-16 AC4 | Pending or rejected designers can't use designer features because their account isn't created until approval. Logging in with the right password shows them their Registration status (Pending, or Rejected with the reason). |
| ID-20 AC2 | Trends count views across the whole platform, as the story asks, not just the designer's own projects. |
| ID-21 | Enquiries are conversations: the designer replies, the customer can answer back, and both can attach files. Only those two people can read the conversation or open its attachments. |

### Test-driven development

New features follow red → green → refactor. Write a failing test for the acceptance criterion first, implement the controller and entity code until it passes, then tidy up with the tests still green.

---

## Continuous Integration

[`.github/workflows/ci.yml`](.github/workflows/ci.yml) runs on every push to `main` and on every pull request:

1. Check out the code
2. Set up Python 3.12 (with pip caching)
3. Install `requirements.txt`
4. Run `python -m pytest -v`

A pull request is merged only after CI passes.

### Branching workflow

1. Branch from `main`: `git checkout -b feature/<short-description>`
2. Write the tests first, then the code
3. Push and open a pull request
4. Merge after a teammate's review and a green CI run

`.gitattributes` keeps every file on LF line endings, so a Windows checkout doesn't rewrite whole files.

---

## Architecture (B-C-E)

```
Browser ─▶ Boundary (routes + templates) ─▶ Control (one class per use case) ─▶ Entity (models + DB)
```

**Rules**
- A boundary route calls **one** controller and contains no business logic.
- Controllers hold the use-case logic and validation, and call entities.
- **Only entities** touch the database.
- A user's ID always comes from the session, never from a form field.

### Project structure

```
Nestfolio-Eeveelution/
├── .github/workflows/ci.yml          GitHub Actions pipeline
├── app/
│   ├── __init__.py                   App factory: config, secrets, time zone, CSRF, security headers
│   ├── boundary/                     One blueprint per actor
│   │   ├── __init__.py               role_required, session checks, forced password change
│   │   ├── auth_boundary.py          Landing, login, register, designer application,
│   │   │                             registration status, change password, logout
│   │   ├── customer_boundary.py      Browse IDPs, project pages, favourites, profile, designers,
│   │   │                             enquiries inbox and replies, reports, photos
│   │   ├── designer_boundary.py      Dashboard, company, portfolio, statistics, trends,
│   │   │                             enquiries inbox and replies, profile
│   │   ├── platform_boundary.py      Categories, activity reports, report downloads
│   │   ├── admin_boundary.py         Dashboard charts, accounts, profiles, applications,
│   │   │                             reported IDPs, announcements
│   │   ├── charts.py                 Line-chart geometry for the SVG charts
│   │   ├── timefmt.py                Friendly inbox times ("2h", "3d", "Today")
│   │   └── templates/                Jinja templates (auth, customer, designer, platform,
│   │                                 admin, shared)
│   ├── control/                      One controller per use case, e.g.
│   │   ├── login_controller.py
│   │   ├── search_idp_controller.py
│   │   ├── add_idp_controller.py
│   │   ├── reply_to_enquiry_controller.py
│   │   ├── enquiry_inbox_controller.py
│   │   ├── generate_report_controller.py
│   │   ├── download_report_controller.py   PDF and Excel export
│   │   ├── view_admin_activity_controller.py
│   │   ├── *_validation.py           Shared input and upload validation
│   │   └── simple_pdf.py             Small built-in PDF writer for reports
│   ├── entity/                       SQLAlchemy models, the only DB access
│   │   ├── user_account.py           UserAccount (all roles)
│   │   ├── user_profile.py           UserProfile (roles managed by User Admin)
│   │   ├── designer_application.py   DesignerApplication
│   │   ├── designer_company.py       DesignerCompany, profile and cover photos
│   │   ├── idp.py                    IDP (ranking, search, visibility)
│   │   ├── idp_category.py           IDPCategory, IDPCategoryPhoto
│   │   ├── idp_photo.py              IDPPhoto
│   │   ├── idp_view.py               IDPView (anonymous view log, trends)
│   │   ├── favourite.py              Favourite
│   │   ├── enquiry.py                Enquiry
│   │   ├── reply.py                  Reply, EnquirySeen (conversation and unread state)
│   │   ├── enquiry_attachment.py     EnquiryAttachment
│   │   ├── report.py                 Report (reported IDPs, removal reasons)
│   │   ├── announcement.py           Announcement, AnnouncementRole
│   │   ├── activity_report.py        ActivityReport (computed, not stored)
│   │   ├── activity_timeline.py      ActivityTimeline (per-hour/day counts for charts)
│   │   ├── encryption.py             EncryptedString column type, phone fingerprint
│   │   └── db.py                     SQLAlchemy instance
│   └── static/                       CSS, UI images and demo photos (idpbg, idpcatbg, idpfp)
├── docs/
│   ├── test-coverage.md              Acceptance criteria → tests
│   └── backend-requirements-id.md    Backend notes for the designer stories
├── tests/                            pytest suite
├── seed.py                           Demo data generator
├── upgrade_phone_hashes.py           One-off upgrade for older databases
├── run.py                            Development server entry point
├── .gitattributes                    LF line endings
└── requirements.txt
```

### Routes

| Prefix | Actor | Main pages |
|--------|-------|------------|
| `/` | Anyone | Landing, `/login`, `/register`, `/register/designer`, `/registration-status`, `/account/password`, `/logout` |
| `/customer` | Customer | Browse, `/projects/<id>`, `/favourites`, `/designers`, `/designers/<id>`, `/enquiries`, `/profile` |
| `/designer` | Designer | Dashboard, `/company`, `/portfolio`, `/statistics`, `/trends`, `/enquiries`, `/profile` |
| `/platform` | Platform Management | Dashboard, `/categories`, `/reports`, `/reports/download` |
| `/admin` | User Admin | Dashboard, `/accounts`, `/profiles`, `/applications`, `/reports`, `/announcements` |

---

## Security

- **Passwords** are hashed with Werkzeug and are never stored or shown in plain text.
- **Personal data at rest:** phone numbers (on accounts, applications and companies) and enquiry contact details are encrypted with Fernet. A separate one-way fingerprint lets the app enforce unique phone numbers without decrypting them.
- **No hard-coded secrets.** `SECRET_KEY` and `ENCRYPTION_KEY` are read from the environment if set. Otherwise they are generated on first run and saved in `instance/` (git-ignored).
- **CSRF protection** on every form (Flask-WTF).
- **Sessions:** HttpOnly, SameSite=Lax cookies (set `SESSION_COOKIE_SECURE=1` when serving over HTTPS). Each request checks that the account is still active and its password unchanged, so suspending a user or changing a password logs out existing sessions.
- **Private conversations:** only an enquiry's customer and designer can read it, reply, or download its attachments. Anyone else gets "not found", so the app never reveals that an enquiry exists.
- **Uploads:** photos are checked with Pillow to be real JPG/PNG images within size limits, and PDFs must start with a real PDF header, so renaming a file isn't enough to get it through.
- **Headers:** `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, and a strict referrer policy.
- **Input safety:** all queries go through SQLAlchemy bound parameters (no raw SQL), search wildcards are escaped, redirects are restricted to this site, and Excel exports are protected against formula injection.

### Keys and the database

- The database lives at `instance/eeveelution.db`.
- **Back up `instance/encryption_key.key` together with the database.** Without it, the encrypted data can't be read. If the database exists but the key file is missing, the app refuses to start rather than quietly making a new key.
- To use your own key:

  ```bash
  python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
  # then set ENCRYPTION_KEY to the printed value
  ```

- If you see *"Could not decrypt a stored value"*, the database was made with a different key. Run `python seed.py` to rebuild it.

---

## Ethics

- **View tracking is anonymous.** A logged view stores only the project, its category and the time. It never stores who viewed it (no customer ID, IP address or session), so reports, charts and trends can't be traced back to a person.
- **Ranking is fair to new and small designers.** The default *Recommended* order ranks projects by views per day since posting, with a one-week head start for new projects. A project is therefore judged on the attention it gets, not on how long it has been online. *Most viewed* and *Newest* remain available for anyone who wants raw counts.
- **Featured designers rotate daily** across all active designers instead of favouring those with the most projects.
- **Designers are told why.** When an admin removes a reported project, the designer gets a notice with the reason, rather than the project silently disappearing.
- **Temporary passwords** from an admin reset are shown once and must be changed at the next login.

---

## Project management

- **Methodology:** Scrum, with one-week sprints and weekly client (tutor) demos
- **Tool:** Taiga — https://tree.taiga.io/project/domdomdominique-eeveelution/timeline

---

## Course context

University of Wollongong — CSIT314 Software Development Methodologies, SIM S4 2026. Final deliverables are due 12 November 2026.
