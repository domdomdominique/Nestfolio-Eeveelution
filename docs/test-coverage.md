# Test coverage by user story

Source: `User Stories.xlsx` (67 stories, each with acceptance criteria). Run everything with
`python -m pytest`.

Every acceptance criterion (AC) is checked by a page-level test in one of three files. A comment
beside each assertion names the AC it covers (for example `# C-03 AC3`).

| Area | Stories | Acceptance tests | Other tests that cover the same code |
|---|---|---|---|
| Customer | C-01 to C-17 | `tests/test_acceptance_customer.py` | `test_register`, `test_login`, `test_customer_pages`, `test_customer_acceptance`, `test_favourites`, `test_search_idp`, `test_landing_page`, `test_confirm_password_on_profile_change`, `test_designer_profile*` |
| Interior Designer | ID-01 to ID-21 | `tests/test_acceptance_designer.py`, `tests/test_role_flows.py` | `test_designer_portfolio`, `test_designer_application`, `test_designer_profile_page`, `test_view_enquiries`, `test_designer_frontend` |
| Platform Management | PM-01 to PM-11 | `tests/test_acceptance_platform_admin.py` | `test_idp_categories`, `test_platform_reports`, `test_platform_frontend` |
| User Admin | UA-01 to UA-18 | `tests/test_acceptance_platform_admin.py` | `test_user_accounts_admin`, `test_user_profiles`, `test_reset_password`, `test_review_reports*`, `test_announcements`, `test_admin_frontend` |

## Known gaps

| Story | Criterion | State |
|---|---|---|
| ID-21 | AC3 (designer replies) and AC5 (customer sees the reply) | Not built. Needs the Reply table in `backend-requirements-id.md` section 5. `test_id21_designer_can_reply_and_customer_sees_it` is marked `xfail` and will start failing (`strict`) once replies exist, so remove the mark then. The sheet also says this needs a customer story to view replies. |
| ID-01 AC5, ID-16 AC4 | Pending or rejected designers cannot use designer features | Met by not creating the account until approval: they cannot log in and are told why. A designer cannot log in to see a "Pending" page. They use the Registration status page (email and password). `backend-requirements-id.md` section 1 describes the alternative. |
| ID-20 AC2 | "Most viewed categories and IDPs across the platform" | Met by `IDPView.trends`. It counts the whole platform, as asked. |

## Behaviour changed to meet the sheet
- **Log out goes to the login page for every role** (C-03, ID-02, PM-02, UA-02 AC2). Customers
  used to land on the public home page, and platform and admin users did too.
- **Logged-in customer pages are not cached** (C-03 AC3), so Back after logging out does not show them.
- **Customer profile shows the date joined** (C-11 AC2).
- **Project cards show the first uploaded photo** as the thumbnail (C-04 AC3).
- **Category and profile detail pages** exist (PM-04 AC3, UA-09 AC3).
- **Reactivate and Suspend dialogs** are only on the page when they apply (UA-13 AC1).
- **Remove project** is available on the reported projects page (UA-17 AC4).

## Also covered
Session and security checks: `test_session_validation.py`, `test_phone_encryption.py`,
`test_unique_phone.py`, and the CSRF test in `test_designer_profile_page.py`.
