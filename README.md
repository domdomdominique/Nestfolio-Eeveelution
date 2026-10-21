# Nestfolio — CSIT314 Group Project (Team Eeveelution)

[![CI](https://github.com/domdomdominique/CSIT314-Eeveelution/actions/workflows/ci.yml/badge.svg)](https://github.com/domdomdominique/CSIT314-Eeveelution/actions/workflows/ci.yml)

**Nestfolio** is an online platform that matches renovation customers with interior designers (IDs). Customers browse and save Interior Design Projects (IDPs), designers showcase their portfolios and receive enquiries, and administrators keep the platform trustworthy.

Built for **CSIT314 Software Development Methodologies** (UOW, SIM S4 2026) with Python + Flask, following the **Boundary–Control–Entity (B-C-E)** design and an agile (Scrum) process with test-driven development and CI.

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

### Customer
- Register, log in, and manage own profile (name, email, phone) and password
- Browse and search IDPs by keyword, filter by category and current/past status, and sort by views or saves
- View an IDP's details (view count is recorded automatically)
- Save IDPs to a favourites list, then search, sort, and remove favourites
- Browse designers and view a designer's profile and portfolio
- Send an enquiry to a designer
- Report an inappropriate IDP

### Interior Designer
- Apply to join the platform with company details (company name, UEN, portfolio URL, experience)
- Log in once the application is approved
- View enquiries sent by customers
- IDPs track view and shortlist (favourite) counts

### User Admin
- Review pending designer applications and approve or reject them
- Review customer reports on IDPs and mark them resolved

### Platform Management
- Dashboard (in progress)

### In progress / planned
- Designers managing company information and their IDP portfolio (create, edit, delete)
- Designer analytics dashboard for IDP views and shortlists
- Platform Management: manage IDP categories and generate daily, weekly, and monthly reports

---

## Tech stack

| Layer      | Technology |
|------------|------------|
| Language   | Python 3.12 |
| Web        | Flask 3.1 (Jinja templates, Pico CSS) |
| Database   | SQLite via Flask-SQLAlchemy |
| Security   | Werkzeug password hashing, Fernet field encryption for phone numbers (`cryptography`) |
| Testing    | pytest |
| CI         | GitHub Actions |
| Deployment | Gunicorn |

---

## Getting started

### 1. Clone the repository

```bash
git clone https://github.com/domdomdominique/CSIT314-Eeveelution.git
cd CSIT314-Eeveelution
```

### 2. Create a virtual environment and install dependencies

**Windows (PowerShell)**
```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

**macOS / Linux / Git Bash**
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Generate the test data

```bash
python seed.py
```

This resets the database and creates repeatable data (fixed random seed):

| Data | Records |
|------|---------|
| Customer accounts | 100 (+1 demo) |
| Designer accounts | 100 (+1 demo), plus 25 approved from applications |
| Designer applications | 100 (60 pending, 25 approved, 15 rejected) |
| Interior Design Projects | 100 across 6 categories |
| Reports | 100 (70 open, 30 resolved) |
| Enquiries | 100 |

### 4. Run the app

```bash
python run.py
```

Open <http://127.0.0.1:5000>.

### Demo logins

All demo accounts use the password `password123`.

| Role | Email |
|------|-------|
| User Admin | `admin@demo.com` |
| Interior Designer | `designer@demo.com` |
| Customer | `customer@demo.com` |
| Platform Management | `platform@demo.com` |

Generated accounts (`customer1@test.com` … `customer100@test.com`, `designer1@test.com` …) also use `password123`. Pending applicants such as `applicant1@test.com` cannot log in until an admin approves them.

---

## Testing

```bash
pytest -v
```

The suite (97 tests at last count) runs against an in-memory SQLite database, so it never touches your local data. There is roughly one test file per use case:

| Test file | Covers |
|-----------|--------|
| `test_login.py`, `test_register.py` | Authentication and sign-up validation |
| `test_designer_application.py` | Designer application, approval, rejection |
| `test_search_idp.py`, `test_customer_pages.py` | Browsing, searching, and viewing IDPs |
| `test_favourites.py` | Saving, searching, and removing favourites |
| `test_designer_profile.py` | Designer profiles and enquiries |
| `test_view_enquiries.py` | Designer enquiry list |
| `test_review_reports.py` | Reporting IDPs and admin review |
| `test_landing_page.py` | Landing page |
| `test_phone_encryption.py` | Field-level encryption of phone numbers |
| `test_customer_acceptance.py` | End-to-end customer acceptance scenarios |

### Test-driven development

New features follow red → green → refactor: write a failing test in `tests/` for the use case, implement the controller and entity code until it passes, then clean up with the tests still green.

---

## Continuous Integration

[`.github/workflows/ci.yml`](.github/workflows/ci.yml) runs on every push to `main` and on every pull request:

1. Check out the code
2. Set up Python 3.12 (with pip caching)
3. Install `requirements.txt`
4. Run `python -m pytest -v`

A pull request should only be merged once CI passes.

### Branching workflow

1. Branch from `main`: `git checkout -b feature/<short-description>`
2. Write tests first, then the code
3. Push and open a pull request
4. Get a teammate's review and a green CI run, then merge

---

## Architecture (B-C-E)

```
Browser ─▶ Boundary (routes + templates) ─▶ Control (one class per use case) ─▶ Entity (models + DB)
```

**Rules**
- A boundary route calls **one** controller.
- Controllers contain the use-case logic and call entities.
- **Only entities** touch the database.

### Project structure

```
CSIT314-Eeveelution/
├── .github/workflows/ci.yml        GitHub Actions pipeline
├── app/
│   ├── __init__.py                 App factory (config, blueprints, DB setup)
│   ├── boundary/                   One blueprint per actor
│   │   ├── auth_boundary.py        Landing, login, register, designer application, logout
│   │   ├── customer_boundary.py    Browse/search IDPs, favourites, profile, designers, enquiries, reports
│   │   ├── designer_boundary.py    Designer home, enquiries
│   │   ├── admin_boundary.py       Designer applications, report review
│   │   ├── platform_boundary.py    Platform Management home
│   │   └── templates/              Jinja templates, one folder per actor
│   ├── control/                    One controller per use case, e.g.
│   │   ├── login_controller.py
│   │   ├── search_idp_controller.py
│   │   ├── save_favourite_controller.py
│   │   ├── review_designer_application_controller.py
│   │   └── …
│   ├── entity/                     SQLAlchemy models — the only DB access
│   │   ├── user_account.py         UserAccount (all four roles)
│   │   ├── designer_application.py DesignerApplication (company info)
│   │   ├── idp.py                  IDP (views, shortlists, categories)
│   │   ├── favourite.py            Favourite
│   │   ├── enquiry.py              Enquiry
│   │   ├── report.py               Report
│   │   ├── encryption.py           EncryptedString column type
│   │   └── db.py                   SQLAlchemy instance
│   └── static/                     CSS and UI images
├── tests/                          pytest suite (one file per use case)
├── seed.py                         Test data generator
├── run.py                          Development server entry point
└── requirements.txt
```

### Routes

| Prefix | Actor | Main pages |
|--------|-------|------------|
| `/` | Anyone | Landing, `/login`, `/register`, `/register/designer`, `/logout` |
| `/customer` | Customer | Browse, `/projects/<id>`, `/favourites`, `/designers`, `/profile` |
| `/designer` | Designer | Home, `/enquiries` |
| `/admin` | User Admin | Home, `/applications`, `/reports` |
| `/platform` | Platform Management | Home |

---

## Configuration and security notes

- The SQLite database is created at `instance/eeveelution.db` (git-ignored).
- Passwords are hashed with Werkzeug; phone numbers are encrypted at rest with Fernet.
- `app/__init__.py` includes a **development-only** encryption key and secret key so the app runs out of the box. For any real deployment, set your own key:

  ```bash
  python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
  # then set ENCRYPTION_KEY to the printed value
  ```

- If you see *"Could not decrypt a stored value"*, your database was made with a different key: delete `instance/eeveelution.db` and run `python seed.py` again.

---

## Project management

- **Methodology:** Scrum, one-week sprints with weekly client (tutor) demos
- **Tool:** Taiga — <!-- add your Taiga project link here -->

---

## Course context

University of Wollongong — CSIT314 Software Development Methodologies, SIM S4 2026. Final deliverables due 12 November 2026.
