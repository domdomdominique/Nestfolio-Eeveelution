# Nestfolio — CSIT314 Group Project (Team Eeveelution)

[![CI](https://github.com/domdomdominique/Nestfolio-Eeveelution/actions/workflows/ci.yml/badge.svg)](https://github.com/domdomdominique/Nestfolio-Eeveelution/actions/workflows/ci.yml)

**Nestfolio** is an online platform that matches renovation customers with interior designers. Customers browse, save and enquire about Interior Design Projects (IDPs). Designers publish a portfolio and track how it performs. Platform Management curates categories and reports on activity, and User Admins keep accounts and content in order.

Built for **CSIT314 Software Development Methodologies** (UOW, SIM S4 2026) with Python and Flask. The code follows the **Boundary–Control–Entity (B-C-E)** design, and the team works in Scrum with test-driven development and continuous integration.

**Status:** all four actors are built, and 66 of the 67 user stories pass their acceptance tests. The one gap is designers replying to enquiries (ID-21 AC3/AC5); see [Known gaps](#known-gaps).

---

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
- Browse designers, view a designer's company profile and portfolio, and send them an enquiry.
- Report an inappropriate IDP (once per project).
- See system announcements on the home page.

### Interior Designer (ID-01 to ID-21)
- Apply to join with company details (company name, UEN, portfolio URL, years of experience).
- Check application status (pending, approved, or rejected with a reason) on the **Registration status** page. Designers can only log in once approved.
- Add, view, edit and delete their **company profile**, including a company photo.
- Manage a **portfolio**: add, edit and delete IDPs with up to 10 JPG/PNG photos each (5 MB per photo), mark projects current or past, and search their own portfolio.
- **Statistics**: view and shortlist counts for each of their IDPs.
- **Trends**: the platform's most viewed categories and IDPs over the last 7 or 30 days.
- View enquiries from customers.
- View and edit their own account details.

### Platform Management (PM-01 to PM-11)
- Create, view, search, update and delete **IDP categories**. These drive the designer forms and customer filters.
- Generate **daily, weekly (Monday to Sunday) and monthly activity reports**: new accounts, new IDPs, total views and shortlists, plus the top IDPs and categories by views and by shortlists.
- **Download** any report as PDF or CSV. CSV cells are protected against formula injection.

### User Admin (UA-01 to UA-18)
- Create, view, search and update **user accounts**, and suspend or reactivate them.
- **Reset a user's password**: a one-time temporary password is generated, and the user must change it at their next login.
- Create, view, search, update and suspend **user profiles** (roles).
- Review **designer applications** and approve or reject them, with a reason.
- Review **reported IDPs**: resolve the report, or remove the project.
- Send and remove **system-wide announcements**.

---

## Tech stack

| Area       | Technology |
|------------|------------|
| Language   | Python 3.12 |
| Web        | Flask 3.1, Jinja templates, Pico CSS |
| Database   | SQLite via Flask-SQLAlchemy |
| Forms      | Flask-WTF (CSRF protection) |
| Images     | Pillow (photo upload validation) |
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

### 3. Generate the test data

```bash
python seed.py
```

This **wipes and rebuilds** the database with repeatable data (it uses a fixed random seed):

| Data | Records |
|------|---------|
| User accounts | 229 in total: 4 demo logins, 100 customers (5 suspended), 100 designers, plus 25 designers approved from applications |
| Designer applications | 100 (60 pending, 25 approved, 15 rejected) |
| Interior Design Projects | 100 across 6 default categories |
| Favourites | 126 |
| Logged IDP views | 3,000 spread over the last 60 days (for reports and trends) |
| Reported IDPs | 100 (70 open, 30 resolved) |
| Enquiries | 100 |
| Categories / user profiles | 6 / 4 defaults |
| Announcements | 3 |

### 4. Run the app

```bash
python run.py
```

Open <http://127.0.0.1:5000>. To turn on the Flask debugger for local work only, run `FLASK_DEBUG=1 python run.py`.

### Demo logins

All demo and generated accounts use the password `password123`.

| Role | Email |
|------|-------|
| User Admin | `admin@demo.com` |
| Interior Designer | `designer@demo.com` |
| Customer | `customer@demo.com` |
| Platform Management | `platform@demo.com` |

Generated accounts use the person's full name run together, e.g. `weimingkoh@test.com`, with a number added for repeated names (`weimingkoh2@test.com`). `seed.py` prints one pending applicant at the end. Pending applicants can't log in, but they can check their application on the Registration status page.

### Upgrading an existing database

There is no migration tool. Normally you delete `instance/eeveelution.db` and run `python seed.py` again. If a database from before phone-uniqueness checks were added needs to keep its records, run this instead:

```bash
python upgrade_phone_hashes.py
```

It adds the phone fingerprint column without deleting anything, and stops if two accounts share a phone number.

---

## Testing

```bash
pytest -v
```

The suite has **393 tests** in 37 test files, plus one expected failure (`xfail`) that marks the designer-reply gap. Tests run against an in-memory SQLite database with throwaway keys, so they never touch your local data.

### Acceptance tests by user story

Every acceptance criterion in the user story sheet (67 stories) is checked by a page-level test. The comment beside each assertion names the criterion it covers (e.g. `# C-03 AC3`).

| Area | Stories | Acceptance tests | Supporting tests |
|------|---------|------------------|------------------|
| Customer | C-01 to C-17 | `test_acceptance_customer.py` | `test_register`, `test_login`, `test_customer_pages`, `test_favourites`, `test_search_idp`, `test_landing_page`, `test_designer_profile*` |
| Interior Designer | ID-01 to ID-21 | `test_acceptance_designer.py`, `test_role_flows.py` | `test_designer_portfolio`, `test_designer_application`, `test_designer_profile_page`, `test_view_enquiries`, `test_designer_frontend` |
| Platform Management | PM-01 to PM-11 | `test_acceptance_platform_admin.py` | `test_idp_categories`, `test_platform_reports`, `test_platform_frontend` |
| User Admin | UA-01 to UA-18 | `test_acceptance_platform_admin.py` | `test_user_accounts_admin`, `test_user_profiles`, `test_reset_password`, `test_review_reports*`, `test_announcements`, `test_admin_frontend` |
| Security and ethics | — | `test_security.py`, `test_ethics.py` | `test_session_validation`, `test_phone_encryption`, `test_unique_phone`, `test_phone_and_email_input` |

The full mapping is in [`docs/test-coverage.md`](docs/test-coverage.md).

### Known gaps

| Story | Criterion | State |
|-------|-----------|-------|
| ID-21 | AC3 (designer replies) and AC5 (customer sees the reply) | Not built yet. `test_id21_designer_can_reply_and_customer_sees_it` is marked `xfail(strict=True)`, so it will start failing once replies exist. Remove the mark at that point. |
| ID-01 AC5, ID-16 AC4 | Pending or rejected designers can't use designer features | Met by not creating the account until approval. Applicants use the Registration status page instead. |

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
│   ├── __init__.py                   App factory: config, secrets, CSRF, security headers, blueprints
│   ├── boundary/                     One blueprint per actor
│   │   ├── __init__.py               role_required, session checks, forced password change
│   │   ├── auth_boundary.py          Landing, login, register, designer application,
│   │   │                             registration status, change password, logout
│   │   ├── customer_boundary.py      Browse IDPs, project pages, favourites, profile,
│   │   │                             designers, enquiries, reports, photos
│   │   ├── designer_boundary.py      Dashboard, company, portfolio, statistics, trends,
│   │   │                             enquiries, profile
│   │   ├── platform_boundary.py      Categories, activity reports, report downloads
│   │   ├── admin_boundary.py         Accounts, profiles, applications, reported IDPs,
│   │   │                             announcements
│   │   └── templates/                Jinja templates (auth, customer, designer, platform,
│   │                                 admin, shared)
│   ├── control/                      About 70 controllers, one per use case, e.g.
│   │   ├── login_controller.py
│   │   ├── search_idp_controller.py
│   │   ├── add_idp_controller.py
│   │   ├── generate_report_controller.py
│   │   ├── reset_password_controller.py
│   │   ├── *_validation.py           Shared input validation
│   │   └── simple_pdf.py             Small built-in PDF writer for reports
│   ├── entity/                       SQLAlchemy models, the only DB access
│   │   ├── user_account.py           UserAccount (all roles)
│   │   ├── user_profile.py           UserProfile (roles managed by User Admin)
│   │   ├── designer_application.py   DesignerApplication
│   │   ├── designer_company.py       DesignerCompany, company photo
│   │   ├── idp.py                    IDP (ranking, search, visibility)
│   │   ├── idp_category.py           IDPCategory
│   │   ├── idp_photo.py              IDPPhoto
│   │   ├── idp_view.py               IDPView (anonymous view log, trends)
│   │   ├── favourite.py              Favourite
│   │   ├── enquiry.py                Enquiry
│   │   ├── report.py                 Report (reported IDPs)
│   │   ├── announcement.py           Announcement
│   │   ├── activity_report.py        ActivityReport (computed, not stored)
│   │   ├── encryption.py             EncryptedString column type, phone fingerprint
│   │   └── db.py                     SQLAlchemy instance
│   └── static/                       CSS and UI images
├── docs/
│   ├── test-coverage.md              Acceptance criteria → tests
│   └── backend-requirements-id.md    Backend notes for the designer stories
├── tests/                            pytest suite
├── seed.py                           Test data generator
├── upgrade_phone_hashes.py           One-off upgrade for older databases
├── run.py                            Development server entry point
└── requirements.txt
```

### Routes

| Prefix | Actor | Main pages |
|--------|-------|------------|
| `/` | Anyone | Landing, `/login`, `/register`, `/register/designer`, `/registration-status`, `/account/password`, `/logout` |
| `/customer` | Customer | Browse, `/projects/<id>`, `/favourites`, `/designers`, `/designers/<id>`, `/profile` |
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
- **Headers:** `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, and a strict referrer policy.
- **Input safety:** all queries go through SQLAlchemy bound parameters (no raw SQL), search wildcards are escaped, redirects are restricted to this site, uploaded images are verified with Pillow, and CSV exports are protected against formula injection.

### Keys and the database

- The database lives at `instance/eeveelution.db`.
- **Back up `instance/encryption_key.key` together with the database.** Without it, the encrypted data can't be read. If the database exists but the key file is missing, the app refuses to start rather than quietly making a new key.
- To use your own key:

  ```bash
  python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
  # then set ENCRYPTION_KEY to the printed value
  ```

- If you see *"Could not decrypt a stored value"*, the database was made with a different key. Delete `instance/eeveelution.db` and run `python seed.py` again.

---

## Ethics

- **View tracking is anonymous.** A logged view stores only the project, its category and the time. It never stores who viewed it (no customer ID, IP address or session), so reports and trends can't be traced back to a person.
- **Ranking is fair to new and small designers.** The default *Recommended* order ranks projects by views per day since posting, with a one-week head start for new projects. A project is therefore judged on the attention it gets, not on how long it has been online. *Most viewed* and *Newest* remain available for anyone who wants raw counts.
- **Featured designers rotate daily** across all active designers instead of favouring those with the most projects.
- **Temporary passwords** from an admin reset are shown once and must be changed at the next login.

---

## Project management

- **Methodology:** Scrum, with one-week sprints and weekly client (tutor) demos
- **Tool:** Taiga — <!-- add your Taiga project link here -->

---

## Course context

University of Wollongong — CSIT314 Software Development Methodologies, SIM S4 2026. Final deliverables are due 12 November 2026.
