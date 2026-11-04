"""Designer portfolio: ID-06 add, ID-07 view, ID-08 search, ID-09 edit, ID-10 delete,
ID-11 status, ID-12 category, ID-13/14 view and shortlist counts."""
import pytest

from app.control.add_idp_controller import AddIDPController
from app.control.delete_idp_controller import DeleteIDPController
from app.control.edit_project_controller import EditProjectController
from app.control.set_idp_status_controller import SetIDPStatusController
from app.control.view_portfolio_controller import ViewPortfolioController
from app.entity.db import db
from app.entity.enquiry import Enquiry
from app.entity.favourite import Favourite
from app.entity.idp import IDP
from app.entity.report import Report
from app.entity.user_account import UserAccount


@pytest.fixture
def people(app):
    designer = UserAccount.create("des@test.com", "password123", "designer", name="Dana Ong")
    other = UserAccount.create("other@test.com", "password123", "designer", name="Olly Ng")
    customer = UserAccount.create("cus@test.com", "password123", "customer", name="Sarah Tan")
    return designer, other, customer


def make_idp(designer, title="Scandinavian Loft", category="Living Room", current=False, **kw):
    idp = IDP(title=title, category=category, designer_id=designer.id, is_current=current, **kw)
    db.session.add(idp)
    db.session.commit()
    return idp


def form(title, description, category, status):
    return {"title": title, "description": description, "category": category, "status": status}


def login(client, email="des@test.com"):
    client.post("/login", data={"email": email, "password": "password123"})


# --- ID-06 add ------------------------------------------------------------

def test_add_idp_saves_it_to_the_designers_portfolio(people):
    designer, _, _ = people
    idp = AddIDPController().add(designer.id, form("  Warm HDB  ", "Bright and calm", "Living Room", "current"))
    assert (idp.title, idp.category, idp.is_current, idp.designer_id) == \
        ("Warm HDB", "Living Room", True, designer.id)
    assert [i.title for i in ViewPortfolioController().view(designer.id)["projects"]] == ["Warm HDB"]


@pytest.mark.parametrize("title,category,status", [
    ("", "Living Room", "current"),            # missing title
    ("   ", "Living Room", "current"),         # blank title
    ("x" * 151, "Living Room", "current"),     # too long
    ("Ok", "Made-up category", "current"),     # ID-12: only existing categories
    ("Ok", "Living Room", "finished"),         # ID-11: only current or past
])
def test_add_idp_rejects_invalid_fields(people, title, category, status):
    designer, _, _ = people
    with pytest.raises(ValueError):
        AddIDPController().add(designer.id, form(title, "", category, status))
    assert IDP.count_for_designer(designer.id) == 0


def test_description_is_limited_to_1000_characters(people):
    designer, _, _ = people
    with pytest.raises(ValueError):
        AddIDPController().add(designer.id, form("Ok", "x" * 1001, "Kitchen", "past"))


# --- ID-07 / ID-08 view and search ------------------------------------------

def test_portfolio_lists_only_own_projects_with_counts(people):
    designer, other, _ = people
    make_idp(designer, "Mine", view_count=12, shortlist_count=3)
    make_idp(other, "Not mine")
    page = ViewPortfolioController().view(designer.id)
    assert [(i.title, i.view_count, i.shortlist_count) for i in page["projects"]] == [("Mine", 12, 3)]
    assert page["counts"] == {"all": 1, "current": 0, "past": 1}


def test_search_matches_title_and_stays_within_own_projects(people):
    designer, other, _ = people
    make_idp(designer, "Modern kitchen", "Kitchen")
    make_idp(designer, "Cosy bedroom", "Bedroom")
    make_idp(other, "Modern loft")
    titles = lambda **kw: [i.title for i in ViewPortfolioController().view(designer.id, **kw)["projects"]]
    assert titles(keyword="modern") == ["Modern kitchen"]
    assert titles(keyword="zzz") == []


def test_search_treats_wildcards_literally(people):
    designer, _, _ = people
    make_idp(designer, "100% natural")
    make_idp(designer, "Plain")
    result = ViewPortfolioController().view(designer.id, keyword="%")["projects"]
    assert [i.title for i in result] == ["100% natural"]


def test_portfolio_filters_by_status_and_category(people):
    designer, _, _ = people
    make_idp(designer, "A", "Kitchen", current=True)
    make_idp(designer, "B", "Kitchen", current=False)
    make_idp(designer, "C", "Bedroom", current=True)
    view = ViewPortfolioController().view
    assert sorted(i.title for i in view(designer.id, status="current")["projects"]) == ["A", "C"]
    assert [i.title for i in view(designer.id, status="past")["projects"]] == ["B"]
    assert sorted(i.title for i in view(designer.id, category="Kitchen")["projects"]) == ["A", "B"]
    assert view(designer.id, status="nonsense")["status"] is None  # bad filter ignored


# --- ID-09 edit ---------------------------------------------------------------

def test_edit_updates_own_idp(people):
    designer, _, _ = people
    idp = make_idp(designer)
    EditProjectController().update(designer.id, idp.id, form("New title", "New text", "Kitchen", "current"))
    idp = IDP.get(idp.id)
    assert (idp.title, idp.description, idp.category, idp.is_current) == \
        ("New title", "New text", "Kitchen", True)


def test_edit_with_invalid_data_changes_nothing(people):
    designer, _, _ = people
    idp = make_idp(designer)
    with pytest.raises(ValueError):
        EditProjectController().update(designer.id, idp.id, form("", "", "Kitchen", "past"))
    assert IDP.get(idp.id).title == "Scandinavian Loft"


def test_designer_cannot_edit_or_load_someone_elses_idp(people):
    designer, other, _ = people
    idp = make_idp(other)
    with pytest.raises(LookupError):
        EditProjectController().update(designer.id, idp.id, form("Hacked", "", "Kitchen", "past"))
    with pytest.raises(LookupError):
        EditProjectController().get_project(designer.id, idp.id)
    assert IDP.get(idp.id).title == "Scandinavian Loft"


# --- ID-10 delete ----------------------------------------------------------------

def test_delete_removes_idp_and_its_dependants(people):
    designer, _, customer = people
    idp = make_idp(designer)
    Favourite.add(customer.id, idp)
    Report.submit(customer.id, idp.id, "Spam or advertising")
    Enquiry.send(designer.id, customer.id, "Sarah", "s@mail.com", "Hello", idp.id)
    DeleteIDPController().delete(designer.id, idp.id)
    assert IDP.get(idp.id) is None
    assert Favourite.query.count() == 0
    assert Report.query.count() == 0
    enquiry = Enquiry.query.one()  # the customer's message is kept, just unlinked
    assert enquiry.idp_id is None


def test_designer_cannot_delete_someone_elses_idp(people):
    designer, other, _ = people
    idp = make_idp(other)
    with pytest.raises(LookupError):
        DeleteIDPController().delete(designer.id, idp.id)
    assert IDP.get(idp.id) is not None


# --- ID-11 status ---------------------------------------------------------------

def test_status_can_be_switched_and_is_saved(people):
    designer, _, _ = people
    idp = make_idp(designer, current=False)
    SetIDPStatusController().set(designer.id, idp.id, "current")
    assert IDP.get(idp.id).is_current is True
    SetIDPStatusController().set(designer.id, idp.id, "past")
    assert IDP.get(idp.id).is_current is False


def test_status_rejects_unknown_value_and_other_designers(people):
    designer, other, _ = people
    mine, theirs = make_idp(designer), make_idp(other)
    with pytest.raises(ValueError):
        SetIDPStatusController().set(designer.id, mine.id, "archived")
    with pytest.raises(LookupError):
        SetIDPStatusController().set(designer.id, theirs.id, "current")


# --- Boundary (pages) ----------------------------------------------------------------

def test_portfolio_page_requires_designer_login(client, people):
    assert client.get("/designer/portfolio").status_code == 302
    login(client, "cus@test.com")
    assert client.get("/designer/portfolio").status_code == 403


def test_portfolio_page_shows_projects_counts_and_search_empty_state(client, people):
    designer, _, _ = people
    make_idp(designer, "Modern kitchen", view_count=3284, shortlist_count=214)
    login(client)
    html = client.get("/designer/portfolio").get_data(as_text=True)
    assert "Modern kitchen" in html and "3,284" in html and "214" in html
    html = client.get("/designer/portfolio?q=nothing").get_data(as_text=True)
    assert "No results found" in html


def test_add_page_creates_project_and_shows_it(client, people):
    login(client)
    response = client.post("/designer/portfolio/new", data={
        "title": "Zen bath", "description": "Calm", "category": "Bathroom", "status": "past"})
    assert response.status_code == 302
    assert "Zen bath" in client.get("/designer/portfolio").get_data(as_text=True)


def test_add_page_shows_error_and_keeps_input(client, people):
    login(client)
    response = client.post("/designer/portfolio/new", data={
        "title": "", "description": "Keep me", "category": "Bathroom", "status": "past"})
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "Keep me" in html and "title" in html.lower()
    assert IDP.query.count() == 0


def test_other_designers_project_is_404_on_edit_and_delete(client, people):
    _, other, _ = people
    idp = make_idp(other)
    login(client)
    assert client.get(f"/designer/portfolio/{idp.id}/edit").status_code == 404
    assert client.post(f"/designer/portfolio/{idp.id}/delete").status_code == 404
    assert client.post(f"/designer/portfolio/{idp.id}/status", data={"status": "past"}).status_code == 404
    assert IDP.get(idp.id) is not None


def test_delete_requires_post(client, people):
    designer, _, _ = people
    idp = make_idp(designer)
    login(client)
    assert client.get(f"/designer/portfolio/{idp.id}/delete").status_code == 405
    client.post(f"/designer/portfolio/{idp.id}/delete")
    assert IDP.get(idp.id) is None
