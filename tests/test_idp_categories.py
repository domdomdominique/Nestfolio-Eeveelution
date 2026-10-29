"""PM-03 to PM-07: Platform Management manages IDP categories."""
import pytest

from app.control.create_category_controller import CreateCategoryController
from app.control.delete_category_controller import DeleteCategoryController
from app.control.search_category_controller import SearchCategoryController
from app.control.search_idp_controller import SearchIDPController
from app.control.update_category_controller import UpdateCategoryController
from app.control.view_category_controller import ViewCategoryController
from app.entity.db import db
from app.entity.idp import IDP
from app.entity.idp_category import IDPCategory
from app.entity.user_account import UserAccount


def make_idp(category, title="Project"):
    designer = UserAccount.query.filter_by(role="designer").first() or \
        UserAccount.create("des@test.com", "password123", "designer", name="Des")
    idp = IDP(title=title, category=category, designer_id=designer.id)
    db.session.add(idp)
    db.session.commit()
    return idp


def test_default_categories_exist_on_first_run(app):
    assert "Kitchen" in IDPCategory.names()
    assert len(ViewCategoryController().list_categories()) == len(IDPCategory.DEFAULTS)


# --- PM-03 Create -------------------------------------------------------------

def test_create_category_appears_in_list_and_customer_filters(app):
    category = CreateCategoryController().create("  Balcony ", "Outdoor spaces")
    assert category.name == "Balcony" and category.description == "Outdoor spaces"
    assert "Balcony" in [c.name for c in ViewCategoryController().list_categories()]
    make_idp("Balcony", "Garden balcony")
    assert ("Balcony", 1) in SearchIDPController().category_counts()
    assert [p.title for p in SearchIDPController().browse(categories=["Balcony"])] == ["Garden balcony"]


def test_description_is_optional(app):
    assert CreateCategoryController().create("Balcony").description == ""


@pytest.mark.parametrize("name, message", [
    ("", "Please enter a category name"),
    ("   ", "Please enter a category name"),
    ("kitchen", "already exists"),  # duplicate, any case
    ("x" * 51, "50 characters or fewer"),
])
def test_invalid_category_is_not_saved(app, name, message):
    before = IDPCategory.query.count()
    with pytest.raises(ValueError, match=message):
        CreateCategoryController().create(name)
    assert IDPCategory.query.count() == before


# --- PM-04 View ---------------------------------------------------------------

def test_view_shows_name_description_and_idp_count(app):
    make_idp("Kitchen")
    make_idp("Kitchen")
    kitchen = next(c for c in ViewCategoryController().list_categories() if c.name == "Kitchen")
    assert kitchen.idp_count == 2
    assert ViewCategoryController().view(kitchen.id).description == "Kitchens and dining areas."


def test_view_missing_category(app):
    with pytest.raises(LookupError):
        ViewCategoryController().view(999)


def test_empty_category_list(app):
    for category in IDPCategory.query.all():
        category.delete()
    assert ViewCategoryController().list_categories() == []


# --- PM-05 Update -------------------------------------------------------------

def test_rename_updates_every_idp_and_filter(app):
    idp = make_idp("Kitchen")
    kitchen = IDPCategory.query.filter_by(name="Kitchen").first()
    UpdateCategoryController().update(kitchen.id, "Kitchen & Dining", "Updated")
    assert db.session.get(IDP, idp.id).category == "Kitchen & Dining"
    assert ("Kitchen & Dining", 1) in SearchIDPController().category_counts()
    assert "Kitchen" not in IDPCategory.names()


def test_keeping_the_same_name_is_allowed(app):
    kitchen = IDPCategory.query.filter_by(name="Kitchen").first()
    assert UpdateCategoryController().update(kitchen.id, "Kitchen", "New text").description == "New text"


@pytest.mark.parametrize("name", ["", "Bedroom"])
def test_update_with_empty_or_duplicate_name_saves_nothing(app, name):
    kitchen = IDPCategory.query.filter_by(name="Kitchen").first()
    with pytest.raises(ValueError):
        UpdateCategoryController().update(kitchen.id, name, "changed")
    db.session.refresh(kitchen)
    assert (kitchen.name, kitchen.description) == ("Kitchen", "Kitchens and dining areas.")


# --- PM-06 Delete -------------------------------------------------------------

def test_delete_unused_category_removes_it_from_filters(app):
    bathroom = IDPCategory.query.filter_by(name="Bathroom").first()
    assert DeleteCategoryController().delete(bathroom.id) == "Bathroom"
    assert "Bathroom" not in IDPCategory.names()
    assert "Bathroom" not in dict(SearchIDPController().category_counts())


def test_category_in_use_cannot_be_deleted_and_says_how_many(app):
    make_idp("Kitchen")
    make_idp("Kitchen")
    kitchen = IDPCategory.query.filter_by(name="Kitchen").first()
    with pytest.raises(ValueError, match="2 IDPs still use it"):
        DeleteCategoryController().delete(kitchen.id)
    assert "Kitchen" in IDPCategory.names()


# --- PM-07 Search -------------------------------------------------------------

def test_search_matches_part_of_the_name_any_case(app):
    assert [c.name for c in SearchCategoryController().search("ROOM")] == ["Bathroom", "Bedroom", "Living Room"]


def test_search_with_no_matches_returns_nothing(app):
    assert SearchCategoryController().search("zzzz") == []
