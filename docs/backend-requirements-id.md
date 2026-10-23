# Backend requirements for the Interior Designer (ID) stories

Written for the backend developers. The ID frontend is in PR #9; these items block the remaining pages.

**Conventions**
- Follow the existing pattern: entity in `app/entity/`, controllers in `app/control/`, no logic in boundaries.
- Every new model must be imported before `db.create_all()` runs.
- There is no migration tool. Everyone resets with: delete `instance/eeveelution.db`, then `python seed.py`. Add the new tables to `seed.py`.
- Designer ids always come from the session, never from a form field.

**Suggested order:** 1 Account at registration, 2 Company, 3 Category, 4 Photo, 5 Reply, 6 Events.

---

## 1. Account at registration with a status (ID-01 AC5, ID-15, ID-16, UA-14, UA-15)

Today no account exists until an admin approves, so pending and rejected designers cannot log in.

Changes:
- `ApplyDesignerController.apply()` creates the `UserAccount` (role `designer`) immediately, and the `DesignerApplication` with `account_id` set.
- Drop `DesignerApplication.password_hash`; the password lives on the account.
- `approve()` only sets `status='approved'`, `reviewed_by`, `reviewed_at`. It no longer creates an account.
- `reject()` is unchanged (`status='rejected'`, `rejection_reason`).
- Add `UserAccount.designer_status`: the application's status, or `'approved'` for a designer with no application (seeded designers).
- `UserAccount.login` is unchanged. The boundary sends pending/rejected designers to a status page.
- `IDP.visible()` must only return IDPs of designers whose status is `approved` and who are not suspended (C-04 AC5, C-13 AC4).
- Email and phone checks simplify, because the account exists from the start.

Frontend builds: the status page (Pending / Rejected with reason) and a guard that blocks other designer pages until approved.

---

## 2. Company (ID-03, ID-04, ID-05, C-13)

Table `company`:

| Column | Type | Rules |
|---|---|---|
| id | int PK | |
| designer_id | int FK user_account.id | UNIQUE, NOT NULL (one per designer) |
| name | varchar(150) | NOT NULL |
| description | text | optional, max 1000 chars |
| address | varchar(255) | required by the form |
| contact_number | varchar(20) | same Singapore format as `clean_phone` |
| email | varchar(120) | valid format |
| uen | varchar(20) | copied from the application |
| website | varchar(255) | optional, must start with http:// or https:// |
| updated_at | datetime | |

Methods: `Company.for_designer(designer_id)`, `create(designer_id, ...)` (raises if one exists), `update(...)`.

Controllers: `AddCompanyController`, `ViewCompanyController`, `UpdateCompanyController`.

Notes:
- `UserAccount.company` should return this record. It currently returns the application, and code reads `.company_name`, `.uen`, `.portfolio_url`, `.status`. Keep those names or tell the frontend the new ones.
- Consider creating the Company from the application data at approval so designers do not retype it.

---

## 3. Category (ID-12, PM-03 to PM-07, C-05)

Table `category`:

| Column | Type | Rules |
|---|---|---|
| id | int PK | |
| name | varchar(60) | UNIQUE (case-insensitive), NOT NULL |
| description | varchar(255) | optional |
| created_at | datetime | |

- Replace `IDP.category` (string) with `IDP.category_id`, FK to `category.id`, NOT NULL.
- Deleting a category that is in use is refused with "Used by N IDPs" (PM-06 AC3).
- Keep an `IDP.category_name` property so customer pages keep working.
- Methods: `Category.list_all()`, `get`, `create`, `update`, `delete`, `search(keyword)`, `idp_count`.
- Seed the six current names.

Frontend builds: the designer dropdown from `Category.list_all()`, posting `category_id`.

---

## 4. Photo (ID-19, C-04 thumbnails, C-06)

Table `photo`:

| Column | Type | Rules |
|---|---|---|
| id | int PK | |
| idp_id | int FK idp.id | NOT NULL, indexed |
| stored_name | varchar(64) | UNIQUE. Random uuid + `.jpg` or `.png`, never the user's filename |
| original_name | varchar(255) | display only |
| size_bytes | int | |
| position | int | 0 = cover |
| uploaded_at | datetime | |

Rules (backend enforces; frontend checks are only for convenience):
- JPG and PNG only. Verify with Pillow (`Image.open` then `verify`, format in `JPEG`/`PNG`), not by extension or MIME type. Set `Image.MAX_IMAGE_PIXELS`.
- At most 5 MB per file and 20 per IDP. Error text: "Only JPG or PNG files up to 5 MB are allowed."
- Store under `instance/uploads/idp/`, outside `static/`.
- Serve through a route that checks the IDP is visible, or that the viewer owns it. Use `send_from_directory` with the correct type.
- Delete files when a photo is removed and when the IDP is deleted. `IDP.delete()` does not know about photos yet, so please hook it.

Methods: `Photo.add(idp, file)`, `remove(photo_id, designer_id)`, `for_idp(idp_id)`, `set_cover(...)`.
Controllers: `UploadPhotosController`, `RemovePhotoController`.

---

## 5. Reply (ID-21)

Table `reply`:

| Column | Type | Rules |
|---|---|---|
| id | int PK | |
| enquiry_id | int FK enquiry.id | NOT NULL, indexed |
| sender_id | int FK user_account.id | NOT NULL |
| message | text | NOT NULL, not empty, max 2000 chars |
| created_at | datetime | |

- Only the enquiry's designer or its customer may read or post.
- Methods: `Reply.add(enquiry_id, sender_id, message)` (checks access), `Reply.for_enquiry(enquiry_id, viewer_id)`. Add `Enquiry.get_for_designer(designer_id, enquiry_id)` and a `replies` relationship ordered by `created_at`.
- Controllers: `ReplyToEnquiryController`, and `ViewMyEnquiriesController` for the customer.
- ID-21 AC5 needs a customer story ("view replies"). Please add it to the story sheet.

---

## 6. Events for Insights and Trends (ID-20, PM-08 to PM-10)

`view_count` and `shortlist_count` have no history, so they cannot give daily charts or date ranges.

Table `idp_event`:

| Column | Type | Rules |
|---|---|---|
| id | int PK | |
| idp_id | int FK idp.id | NOT NULL |
| event_type | varchar(12) | `view`, `shortlist` or `unshortlist` |
| customer_id | int FK user_account.id | nullable |
| created_at | datetime | NOT NULL |

- Indexes: `(idp_id, event_type, created_at)` and `(event_type, created_at)`.
- Write a row in `IDP.record_view()` and in `Favourite.add` / `Favourite.remove`. Keep the existing counters as totals.
- Queries needed: `daily_counts(designer_id, start, end, type)`, `top_categories(start, end)`, `top_idps(start, end)` (platform-wide, for ID-20 AC2).
- The PM daily, weekly and monthly reports reuse the same table.
