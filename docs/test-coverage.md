# Test coverage by user story

Run everything with `python -m pytest`. This table says which tests cover each story.

The story sheet is not in the repo, so story titles below come from the code comments, and the
coverage is judged against how each story is built, not against the sheet's acceptance criteria.
Check each row against the sheet before the demo.

## Customer

| Story | What | Tests |
|---|---|---|
| C-01 | Register | `test_register.py`, `test_customer_pages.py` (register) |
| C-02 | Log in | `test_login.py`, `test_customer_pages.py` (login as role), `test_role_flows.py` |
| C-03 | Log out | `test_landing_page.py`, `test_customer_pages.py` (logout), `test_role_flows.py` |
| C-04 | Search IDPs | `test_search_idp.py`, `test_customer_acceptance.py` |
| C-05 | Filter by category | `test_customer_pages.py` (browse filters) |
| C-06 | View an IDP | `test_customer_pages.py` (view count, 404), `test_customer_acceptance.py` (not available) |
| C-07 | Save to favourites | `test_favourites.py`, `test_customer_acceptance.py` |
| C-08 | View favourites | `test_favourites.py`, `test_customer_acceptance.py` (empty list) |
| C-09 | Search favourites | `test_favourites.py`, `test_customer_acceptance.py` |
| C-10 | Remove favourite | `test_favourites.py` |
| C-11 | View profile | `test_customer_pages.py` |
| C-12 | Update profile | `test_customer_pages.py`, `test_confirm_password_on_profile_change.py` |
| C-13 | View designer profile | `test_designer_profile.py`, `test_designer_profile_page.py` |
| C-14 | Change password | `test_customer_pages.py`, `test_customer_acceptance.py`, `test_session_validation.py` |
| C-15 | Report an IDP | `test_customer_pages.py`, `test_customer_acceptance.py` |
| C-16 | Contact designer | `test_customer_pages.py` (enquiry) |
| C-17 | Sort IDPs | `test_customer_pages.py`, `test_landing_page.py` |

## Interior Designer

| Story | What | Tests |
|---|---|---|
| ID-01 | Log in (pending/rejected message) | `test_role_flows.py`, `test_designer_application.py` (login explains pending) |
| ID-02 | Log out | `test_role_flows.py` |
| ID-03 to ID-05 | Company: add, view, edit, delete | `test_role_flows.py` |
| ID-06 to ID-12 | Add, list, search, edit, delete, status, category | `test_designer_portfolio.py` |
| ID-13, ID-14 | View and shortlist counts | `test_designer_portfolio.py`, `test_role_flows.py` (statistics page) |
| ID-15, ID-16 | Application pending / rejected | `test_designer_application.py` |
| ID-17, ID-18 | View and edit own profile | `test_designer_profile_page.py`, `test_confirm_password_on_profile_change.py` |
| ID-19 | Project photos | `test_role_flows.py` (upload checks, serving, removal) |
| ID-20 | Customer trends | `test_role_flows.py` |
| ID-21 | View enquiries | `test_view_enquiries.py`, `test_designer_frontend.py` |

Not built yet: replying to enquiries (ID-21 AC5) and an account at registration for pending designers.
See `backend-requirements-id.md`.

## Platform Management

| Story | What | Tests |
|---|---|---|
| PM-01, PM-02 | Log in, log out | `test_role_flows.py` |
| PM-03 to PM-07 | Create, view, update, delete, search categories | `test_idp_categories.py`, `test_platform_frontend.py` |
| PM-08 to PM-10 | Daily, weekly, monthly reports | `test_platform_reports.py`, `test_platform_frontend.py` |
| PM-11 | Download PDF / CSV | `test_platform_reports.py` (incl. CSV formula escaping), `test_platform_frontend.py` |

## User Admin

| Story | What | Tests |
|---|---|---|
| UA-01, UA-02 | Log in, log out | `test_role_flows.py` |
| UA-03 to UA-07 | Create, view, update, suspend, search account | `test_user_accounts_admin.py`, `test_admin_frontend.py` |
| UA-08 to UA-12 | Profiles: create, view, update, suspend, search | `test_user_profiles.py`, `test_admin_frontend.py` |
| UA-13 | Reactivate account | `test_user_accounts_admin.py`, `test_admin_frontend.py` |
| UA-14, UA-15 | Approve / reject designer application | `test_designer_application.py` |
| UA-16 | Reset password (forced change) | `test_reset_password.py`, `test_admin_frontend.py` |
| UA-17 | Review reports: dismiss or remove project | `test_review_reports.py`, `test_review_reports_actions.py` |
| UA-18 | Announcements | `test_announcements.py`, `test_admin_frontend.py` |

## Also covered
Session and security checks: `test_session_validation.py`, `test_phone_encryption.py`, `test_unique_phone.py`,
and the CSRF test in `test_designer_profile_page.py`.
