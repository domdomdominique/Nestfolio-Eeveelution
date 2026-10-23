"""Log in and sign-up pages offer a 'Show password' checkbox."""


def test_login_page_has_show_password_checkbox(client):
    html = client.get("/login").get_data(as_text=True)
    assert "data-toggle-password" in html and "Show password" in html


def test_customer_and_designer_sign_up_pages_have_it(client):
    assert "data-toggle-password" in client.get("/register").get_data(as_text=True)
    assert "data-toggle-password" in client.get("/register/designer").get_data(as_text=True)


def test_checkbox_is_not_checked_by_default(client):
    html = client.get("/login").get_data(as_text=True)
    marker = html.index("data-toggle-password")
    assert "checked" not in html[marker - 80: marker + 80]
