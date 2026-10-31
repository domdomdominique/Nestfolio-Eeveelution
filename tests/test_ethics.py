"""Ethics checklist: hashed passwords, safe search, anonymous view tracking, fair ranking."""
from datetime import datetime, timedelta

from app.control.search_idp_controller import SearchIDPController
from app.entity.db import db
from app.entity.idp import IDP
from app.entity.idp_view import IDPView
from app.entity.user_account import UserAccount


def designer(email):
    return UserAccount.create(email, "password123", "designer", name=email.split("@")[0])


def project(owner, title, views, age_days):
    idp = IDP(title=title, category="Kitchen", designer_id=owner.id, view_count=views,
              created_at=datetime.now() - timedelta(days=age_days))
    db.session.add(idp)
    db.session.commit()
    return idp


def test_passwords_are_stored_hashed(app):
    account = UserAccount.create("a@test.com", "password123", "customer")
    assert "password123" not in account.password_hash and account.password_hash.startswith(("scrypt:", "pbkdf2:"))
    assert account.check_password("password123") and not account.check_password("password124")


def test_search_treats_sql_and_like_characters_as_plain_text(app):
    d = designer("des@test.com")
    project(d, "Loft", 1, 1)
    project(d, "100% Wood", 1, 1)
    search = SearchIDPController()
    assert [p.title for p in search.browse("%")] == ["100% Wood"]  # % is not a wildcard
    assert search.browse("_oft") == []                              # nor is _
    assert search.browse("'; DROP TABLE idp; --") == []
    assert len(search.browse()) == 2                                 # table is intact


def test_view_tracking_stores_nothing_about_the_viewer(app):
    assert {c.name for c in IDPView.__table__.columns} == {"id", "idp_id", "category", "viewed_at"}


def test_recommended_ranking_lets_a_new_project_compete(app):
    big, small = designer("big@test.com"), designer("small@test.com")
    old_hit = project(big, "Old hit", views=300, age_days=400)    # ~0.7 views a day
    fresh = project(small, "Fresh find", views=40, age_days=2)    # ~4.4 views a day
    quiet = project(small, "Brand new", views=0, age_days=0)
    by_views = [p.title for p in SearchIDPController().browse(sort="views")]
    assert by_views == ["Old hit", "Fresh find", "Brand new"]      # raw counts: old hit wins
    recommended = [p.title for p in SearchIDPController().browse()]  # default is fair
    assert recommended == ["Fresh find", "Old hit", "Brand new"]
    assert quiet in IDP.popular(limit=4)                             # unseen projects still appear


def test_featured_designers_are_not_just_the_busiest(app):
    busy, small = designer("busy@test.com"), designer("small@test.com")
    for i in range(5):
        project(busy, f"Busy {i}", 5, 1)
    project(small, "Only one", 0, 1)
    assert set(IDP.featured_designer_ids(limit=5)) == {busy.id, small.id}
    assert IDP.featured_designer_ids(limit=1) == IDP.featured_designer_ids(limit=1)  # stable within a day
