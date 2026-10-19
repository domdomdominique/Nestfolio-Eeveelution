"""Acceptance criteria for the Sprint 2 customer stories that the earlier
customer-page tests did not cover (C-04, C-05, C-06, C-07, C-08, C-09, C-14, C-15)."""
import pytest

from app.control.change_password_controller import ChangePasswordController
from app.control.login_controller import LoginController
from app.control.report_idp_controller import ReportIDPController
from app.control.save_favourite_controller import SaveFavouriteController
from app.control.search_idp_controller import SearchIDPController
from app.control.view_idp_controller import ViewIDPController
from app.control.view_landing_page_controller import ViewLandingPageController
from app.entity.db import db
from app.entity.idp import IDP
from app.entity.report import Report
from app.entity.user_account import UserAccount


def setup_data():
    designer = UserAccount.create("des@test.com", "password123", "designer", name="Dana Ong")
    banned = UserAccount.create("ban@test.com", "password123", "designer", name="Ben Ban")
    banned.is_suspended = True
    customer = UserAccount.create("cus@test.com", "password123", "customer", name="Sarah Tan")
    loft = IDP(title="Scandinavian Loft", category="Living Room", designer_id=designer.id,
               description="Bright open-plan flat with teak shelving", view_count=10)
    kitchen = IDP(title="Modern Kitchen", category="Kitchen", designer_id=designer.id)
    hidden = IDP(title="Hidden Kitchen", category="Kitchen", designer_id=banned.id,
                 description="teak cabinets", view_count=999)
    db.session.add_all([loft, kitchen, hidden])
    db.session.commit()
    return customer, loft, kitchen, hidden


def login(client, email="cus@test.com"):
    client.post("/login", data={"email": email, "password": "password123"})


# --- C-04 Search IDPs ------------------------------------------------------

def test_search_matches_description(app):
    setup_data()
    assert [p.title for p in SearchIDPController().browse("teak")] == ["Scandinavian Loft"]


def test_suspended_designers_projects_are_hidden_everywhere(app):
    _, _, _, hidden = setup_data()
    search = SearchIDPController()
    assert hidden not in search.browse()
    assert hidden not in search.browse(categories=["Kitchen"])
    assert dict(search.category_counts())["Kitchen"] == 1
    assert hidden not in ViewLandingPageController().view()["popular"]


def test_browse_page_says_no_results_found(client, app):
    setup_data()
    page = client.get("/customer/?q=zzzz").get_data(as_text=True)
    assert "No results found" in page


# --- C-05 Filter by category -------------------------------------------------

def test_filter_with_no_matches_says_no_results_found(client, app):
    setup_data()
    page = client.get("/customer/?category=Bathroom").get_data(as_text=True)
    assert "No results found" in page


# --- C-06 View IDP -----------------------------------------------------------

def test_missing_project_shows_not_available_message(client, app):
    setup_data()
    response = client.get("/customer/projects/999")
    assert response.status_code == 404
    assert "Project not available" in response.get_data(as_text=True)


def test_suspended_designers_project_is_not_available(client, app):
    _, _, _, hidden = setup_data()
    with pytest.raises(LookupError):
        ViewIDPController().view(hidden.id)
    assert "Project not available" in client.get(f"/customer/projects/{hidden.id}").get_data(as_text=True)


# --- C-07 Favourite IDPs -----------------------------------------------------

def test_saving_shows_a_confirmation(client, app):
    _, loft, _, _ = setup_data()
    login(client)
    page = client.post(f"/customer/favourites/{loft.id}", follow_redirects=True).get_data(as_text=True)
    assert "Saved “Scandinavian Loft” to your favourites" in page


def test_saving_again_says_already_saved(app):
    customer, loft, _, _ = setup_data()
    controller = SaveFavouriteController()
    assert controller.save(customer.id, loft.id)[1] is True
    assert controller.save(customer.id, loft.id)[1] is False
    assert loft.shortlist_count == 1


def test_saved_project_page_shows_saved(client, app):
    customer, loft, _, _ = setup_data()
    SaveFavouriteController().save(customer.id, loft.id)
    login(client)
    assert "Saved to favourites" in client.get(f"/customer/projects/{loft.id}").get_data(as_text=True)


# --- C-08 View / C-09 Search favourites ----------------------------------------

def test_empty_favourites_message(client, app):
    setup_data()
    login(client)
    assert "You have no saved projects yet" in client.get("/customer/favourites").get_data(as_text=True)


def test_favourites_search_with_no_matches_says_no_results_found(client, app):
    customer, loft, _, _ = setup_data()
    SaveFavouriteController().save(customer.id, loft.id)
    login(client)
    page = client.get("/customer/favourites?q=zzzz").get_data(as_text=True)
    assert "No results found" in page


# --- C-15 Report IDP ---------------------------------------------------------

def test_customer_cannot_report_same_project_twice(app):
    customer, loft, _, _ = setup_data()
    controller = ReportIDPController()
    controller.report(customer.id, loft.id, "Other", "first")
    with pytest.raises(ValueError, match="already reported"):
        controller.report(customer.id, loft.id, "Spam or advertising")
    assert Report.count_open() == 1


def test_report_twice_from_page_shows_error(client, app):
    customer, loft, _, _ = setup_data()
    login(client)
    client.post(f"/customer/projects/{loft.id}/report", data={"reason": "Other"})
    page = client.post(f"/customer/projects/{loft.id}/report", data={"reason": "Other"},
                       follow_redirects=True).get_data(as_text=True)
    assert "already reported this project" in page


def test_different_customers_can_report_same_project(app):
    customer, loft, _, _ = setup_data()
    other = UserAccount.create("other@test.com", "password123", "customer")
    ReportIDPController().report(customer.id, loft.id, "Other")
    ReportIDPController().report(other.id, loft.id, "Other")
    assert Report.count_open() == 2


# --- C-14 Change password ----------------------------------------------------

def test_old_password_no_longer_works_after_change(app):
    customer, _, _, _ = setup_data()
    ChangePasswordController().change(customer.id, "password123", "newpassword1", "newpassword1")
    assert LoginController().login("cus@test.com", "password123") is None
    assert LoginController().login("cus@test.com", "newpassword1") is not None
