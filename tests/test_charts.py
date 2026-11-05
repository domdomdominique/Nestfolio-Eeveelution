"""Over-time charts on the Reports (PM-08 to PM-10), Statistics (ID-13, ID-14) and Trends (ID-20) pages."""
from datetime import date, datetime, timedelta

from app.boundary.charts import line_chart
from app.control.generate_report_controller import GenerateReportController
from app.control.view_idp_statistics_controller import ViewIDPStatisticsController
from app.control.view_trends_controller import ViewTrendsController
from app.entity.activity_timeline import ActivityTimeline
from app.entity.db import db
from app.entity.favourite import Favourite
from app.entity.idp import IDP
from app.entity.idp_view import IDPView
from app.entity.user_account import UserAccount

DAY = date(2026, 10, 13)  # a Tuesday


def at(day, hour=12):
    return datetime(day.year, day.month, day.day, hour)


def setup_activity():
    """Designer A's loft: 3 views on 13 Oct (0:00, 9:00, 9:30) and 1 on 15 Oct, saved once on 13 Oct.
    Designer B's kitchen: 2 views on 13 Oct."""
    a = UserAccount.create("a@test.com", "password123", "designer", name="A")
    b = UserAccount.create("b@test.com", "password123", "designer", name="B")
    customer = UserAccount.create("c@test.com", "password123", "customer", name="C")
    loft = IDP(title="Loft", category="Living Room", designer_id=a.id, created_at=at(DAY, 0))
    kitchen = IDP(title="Kitchen", category="Kitchen", designer_id=b.id, created_at=at(DAY, 0))
    db.session.add_all([loft, kitchen])
    db.session.commit()
    for moment in (at(DAY, 0), at(DAY, 9), at(DAY, 9) + timedelta(minutes=30), at(DAY + timedelta(days=2))):
        db.session.add(IDPView(idp_id=loft.id, category=loft.category, viewed_at=moment))
    for _ in range(2):
        db.session.add(IDPView(idp_id=kitchen.id, category=kitchen.category, viewed_at=at(DAY)))
    db.session.add(Favourite(customer_id=customer.id, idp_id=loft.id, saved_at=at(DAY)))
    db.session.commit()
    return a, b, loft, kitchen


# --- ActivityTimeline (Entity) -------------------------------------------------------------

def test_weekly_timeline_has_every_day_with_zeros(app):
    setup_activity()
    t = GenerateReportController().weekly(DAY).timeline()
    assert t.labels == ["12 Oct", "13 Oct", "14 Oct", "15 Oct", "16 Oct", "17 Oct", "18 Oct"]
    assert t.views == [0, 5, 0, 1, 0, 0, 0]
    assert t.shortlists == [0, 1, 0, 0, 0, 0, 0]


def test_daily_timeline_is_per_hour(app):
    setup_activity()
    t = GenerateReportController().daily(DAY).timeline()
    assert len(t.labels) == 24 and t.labels[9] == "09:00"
    assert t.views[0] == 1 and t.views[9] == 2 and t.views[12] == 2
    assert t.total_views == GenerateReportController().daily(DAY).total_views  # chart matches the report


def test_monthly_timeline_covers_the_whole_month(app):
    setup_activity()
    t = GenerateReportController().monthly(2026, 10).timeline()
    assert len(t.views) == 31 and t.total_views == 6


def test_designer_timeline_only_counts_own_projects(app):
    a, b, loft, kitchen = setup_activity()
    t = ActivityTimeline(DAY, DAY + timedelta(days=7), designer_id=a.id)
    assert t.total_views == 4 and t.total_shortlists == 1


def test_removed_projects_are_left_out_of_platform_trends(app):
    a, b, loft, kitchen = setup_activity()
    kitchen.remove()
    t = ActivityTimeline(DAY, DAY + timedelta(days=7), visible_only=True)
    assert t.total_views == 4


def test_last_days_ends_today(app):
    t = ActivityTimeline.last_days(7)
    assert len(t.labels) == 7 and t.labels[-1] == date.today().strftime("%d %b")


# --- Controllers -----------------------------------------------------------------------------

def test_statistics_and_trends_controllers_return_timelines(app):
    a, *_ = setup_activity()
    assert len(ViewIDPStatisticsController().activity(a.id).views) == 30
    assert len(ViewTrendsController().view(a.id, 7)["timeline"].views) == 7


# --- line_chart (Boundary helper) ------------------------------------------------------------

def test_chart_axis_is_rounded_up_and_points_fit_inside():
    c = line_chart(["a", "b", "c"], [0, 7, 3])
    assert [t["value"] for t in c["ticks"]] == [0, 2, 4, 6, 8]  # even steps, top just above 7
    assert all(c["left"] <= p["x"] <= c["right"] and p["y"] <= c["base"] for p in c["points"])
    assert c["total"] == 10 and c["peak"] == 7
    assert [t["value"] for t in line_chart(["a"], [108])["ticks"]] == [0, 30, 60, 90, 120]


def test_chart_shows_a_limited_number_of_x_labels():
    labels = [f"{d:02d} Oct" for d in range(1, 32)]
    c = line_chart(labels, [1] * 31)
    assert 2 <= len(c["x_labels"]) <= 9 and c["x_labels"][0]["text"] == "01 Oct"
    hours = line_chart([f"{h:02d}:00" for h in range(24)], [0] * 24)
    gaps = [b["x"] - a["x"] for a, b in zip(hours["x_labels"], hours["x_labels"][1:])]
    assert max(gaps) - min(gaps) < 1  # evenly spaced, none squashed together


def test_days_still_to_come_are_left_off_the_line(app):
    t = GenerateReportController().weekly(date.today()).timeline()
    today = date.today().weekday()  # 0 = Monday
    assert all(v is not None for v in t.views[:today + 1])
    assert all(v is None for v in t.views[today + 1:])
    c = line_chart(t.labels, t.views)
    assert len(c["points"]) == today + 1 and len(c["x_labels"]) == 7  # every day still labelled


def test_chart_with_no_activity_still_draws():
    c = line_chart(["a", "b"], [0, 0])
    assert c["peak"] == 0 and c["ticks"][-1]["value"] == 4


# --- Pages (Boundary) ------------------------------------------------------------------------

def login(client, email, role):
    UserAccount.create(email, "password123", role, name="Tester")
    client.post("/login", data={"email": email, "password": "password123", "role": role})


def test_reports_page_shows_charts(client, app):
    setup_activity()
    login(client, "pm@test.com", "platform")
    page = client.get("/platform/reports?kind=weekly&value=2026-10-13").get_data(as_text=True)
    assert page.count("<svg viewBox") >= 2
    assert "Views per day" in page and "New shortlists per day" in page
    assert "13 Oct: 5 views" in page  # tooltip on the point


def test_daily_report_chart_is_per_hour(client, app):
    setup_activity()
    login(client, "pm@test.com", "platform")
    page = client.get("/platform/reports?kind=daily&value=2026-10-13").get_data(as_text=True)
    assert "Views per hour" in page and "09:00: 2 views" in page


def test_statistics_page_shows_charts(client, app):
    setup_activity()
    client.post("/login", data={"email": "a@test.com", "password": "password123", "role": "designer"})
    page = client.get("/designer/statistics").get_data(as_text=True)
    assert "Views per day" in page and "New shortlists per day" in page and "<svg" in page


def test_trends_page_shows_chart(client, app):
    a, b, loft, kitchen = setup_activity()
    db.session.add(IDPView(idp_id=loft.id, category=loft.category, viewed_at=datetime.now()))
    db.session.commit()
    client.post("/login", data={"email": "a@test.com", "password": "password123", "role": "designer"})
    page = client.get("/designer/trends?days=7").get_data(as_text=True)
    assert "Project views per day across the platform, last 7 days" in page and "<svg" in page
