"""User Admin pages (UA-03 to UA-18) and the forced password change after a reset (UA-16)."""
from app.entity.announcement import Announcement
from app.entity.user_account import UserAccount
from app.entity.user_profile import UserProfile


def login(client, email, password="password123"):
    client.post("/login", data={"email": email, "password": password})


def admin_client(client):
    UserAccount.create("admin@test.com", "password123", "admin", name="Ann Admin")
    login(client, "admin@test.com")


def new_account(client, email="new@test.com", profile="customer"):
    return client.post("/admin/accounts/new", data={
        "name": "New User", "email": email, "phone": "91234567",
        "password": "password123", "profile": profile})


def test_pages_are_admin_only(client, app):
    assert client.get("/admin/accounts").status_code == 302
    UserAccount.create("c@test.com", "password123", "customer", name="C")
    login(client, "c@test.com")
    for path in ("/admin/accounts", "/admin/profiles", "/admin/announcements"):
        assert client.get(path).status_code == 403


def test_create_view_search_and_edit_account(client, app):
    admin_client(client)
    assert new_account(client).status_code == 302
    account = UserAccount.query.filter_by(email="new@test.com").one()
    assert b"New User" in client.get(f"/admin/accounts/{account.id}").data
    assert b"new@test.com" in client.get("/admin/accounts?q=new").data
    assert b"No results found" in client.get("/admin/accounts?q=zzzz").data
    client.post(f"/admin/accounts/{account.id}/edit", data={
        "name": "Renamed", "email": "new@test.com", "phone": "91234567", "profile": "customer"})
    assert UserAccount.get(account.id).name == "Renamed"


def test_create_account_shows_error_for_duplicate_email(client, app):
    admin_client(client)
    new_account(client)
    assert b"already registered" in new_account(client).data


def test_suspend_and_reactivate_account(client, app):
    admin_client(client)
    new_account(client)
    account = UserAccount.query.filter_by(email="new@test.com").one()
    client.post(f"/admin/accounts/{account.id}/suspend")
    assert UserAccount.get(account.id).is_suspended
    client.post(f"/admin/accounts/{account.id}/reactivate")
    assert not UserAccount.get(account.id).is_suspended


def test_admin_cannot_move_themselves_to_another_profile(client, app):
    admin_client(client)
    me = UserAccount.query.filter_by(email="admin@test.com").one()
    page = client.post(f"/admin/accounts/{me.id}/edit", data={
        "name": "Ann Admin", "email": "admin@test.com", "phone": "91234567", "profile": "customer"})
    assert b"cannot change your own" in page.data
    assert UserAccount.get(me.id).role == "admin"


def test_reset_shows_temporary_password_once_and_forces_a_change(client, app):
    admin_client(client)
    new_account(client)
    account = UserAccount.query.filter_by(email="new@test.com").one()
    page = client.post(f"/admin/accounts/{account.id}/reset-password")
    assert b"Temporary password" in page.data
    assert b"Temporary password" not in client.get(f"/admin/accounts/{account.id}").data

    temporary = UserAccount.get(account.id)
    assert temporary.must_change_password
    user = app.test_client()
    # the password is random, so reset to a known one the way the controller would
    temporary.reset_password("Temp12345678")
    login(user, "new@test.com", "Temp12345678")
    assert user.get("/customer/").headers["Location"].endswith("/account/password")
    done = user.post("/account/password", data={
        "current_password": "Temp12345678", "new_password": "BrandNew123", "confirm_password": "BrandNew123"})
    assert done.status_code == 302
    assert not UserAccount.get(account.id).must_change_password
    assert user.get("/customer/").status_code == 200


def test_profiles_create_edit_and_suspend(client, app):
    admin_client(client)
    client.post("/admin/profiles/new", data={"name": "Moderator", "description": "Checks posts"})
    profile = UserProfile.query.filter_by(name="Moderator").one()
    assert b"Moderator" in client.get("/admin/profiles?q=mod").data
    client.post(f"/admin/profiles/{profile.id}/edit", data={"name": "Mod Team", "description": ""})
    assert UserProfile.get(profile.id).name == "Mod Team"
    client.post(f"/admin/profiles/{profile.id}/suspend")
    assert not UserProfile.get(profile.id).is_active
    admin_profile = UserProfile.by_key("admin")
    client.post(f"/admin/profiles/{admin_profile.id}/suspend")
    assert UserProfile.get(admin_profile.id).is_active


def test_send_announcement_and_it_appears_on_admin_home(client, app):
    admin_client(client)
    client.post("/admin/announcements", data={"title": "Hello all", "message": "Welcome back"})
    assert Announcement.query.count() == 1
    assert b"Hello all" in client.get("/admin/").data
    assert b"Please enter both" in client.post("/admin/announcements", data={"title": "", "message": ""}).data


def test_logged_in_customer_sees_announcement_on_home_page(client, app):
    admin = UserAccount.create("admin@test.com", "password123", "admin", name="Ann")
    Announcement.send(admin.id, "Big news", "Read me")
    UserAccount.create("c@test.com", "password123", "customer", name="C")
    assert b"Big news" not in client.get("/").data
    login(client, "c@test.com")
    assert b"Big news" in client.get("/").data


def test_account_created_by_admin_must_change_password_at_first_login(client, app):
    admin_client(client)
    new_account(client)
    user = app.test_client()
    login(user, "new@test.com")
    assert user.get("/customer/").headers["Location"].endswith("/account/password")


def test_logout_and_wrong_password_while_a_change_is_pending(client, app):
    admin_client(client)
    new_account(client)
    user = app.test_client()
    login(user, "new@test.com")
    wrong = user.post("/account/password", data={
        "current_password": "nope", "new_password": "BrandNew123", "confirm_password": "BrandNew123"})
    assert b"current password is incorrect" in wrong.data
    assert UserAccount.query.filter_by(email="new@test.com").one().must_change_password
    assert user.get("/logout").status_code == 302
    assert "/account/password" not in user.get("/customer/profile").headers["Location"]  # logged out: login page


def test_change_password_page_has_no_customer_navigation(client, app):
    admin_client(client)
    new_account(client, profile="designer")
    user = app.test_client()
    login(user, "new@test.com")
    page = user.get("/account/password").get_data(as_text=True)
    assert "Choose a new password" in page and "My Favourites" not in page


def test_account_list_is_paged_and_keeps_the_search(client, app):
    admin_client(client)
    for n in range(30):
        UserAccount.create(f"u{n}@test.com", "password123", "customer", name=f"User {n:02d}")
    first = client.get("/admin/accounts?q=u").get_data(as_text=True)
    assert "User 00" in first and "User 29" not in first
    assert "q=u&amp;page=2" in first or "page=2&amp;q=u" in first
    assert "User 29" in client.get("/admin/accounts?q=u&page=2").get_data(as_text=True)
    assert client.get("/admin/accounts?page=999").status_code == 200  # out of range is clamped
