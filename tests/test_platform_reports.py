"""PM-08 to PM-11: Platform Management generates and downloads activity reports."""
import io
from datetime import date, datetime

import pytest
from openpyxl import load_workbook

from app.control.download_report_controller import DownloadReportController
from app.control.generate_report_controller import GenerateReportController
from app.entity.activity_report import ActivityReport
from app.entity.db import db
from app.entity.favourite import Favourite
from app.entity.idp import IDP
from app.entity.idp_view import IDPView
from app.entity.user_account import UserAccount

DAY = date(2026, 10, 13)  # a Tuesday


def at(day, hour=12):
    return datetime(day.year, day.month, day.day, hour)


def setup_activity():
    """On 13 Oct: 2 accounts, 2 IDPs, 3 views of the loft + 1 of the kitchen, 1 shortlist.
    On 15 Oct (same week): 1 view. On 2 Nov: 1 view."""
    designer = UserAccount.create("des@test.com", "password123", "designer", name="Des")
    customer = UserAccount.create("cus@test.com", "password123", "customer", name="Cus")
    designer.created_at = customer.created_at = at(DAY)
    loft = IDP(title="Scandi Loft", category="Living Room", designer_id=designer.id, created_at=at(DAY))
    kitchen = IDP(title="Teak Kitchen", category="Kitchen", designer_id=designer.id, created_at=at(DAY))
    db.session.add_all([loft, kitchen])
    db.session.commit()
    for hour in (0, 9, 23):
        db.session.add(IDPView(idp_id=loft.id, category=loft.category, viewed_at=at(DAY, hour)))
    db.session.add(IDPView(idp_id=kitchen.id, category=kitchen.category, viewed_at=at(DAY)))
    db.session.add(IDPView(idp_id=kitchen.id, category=kitchen.category, viewed_at=at(date(2026, 10, 15))))
    db.session.add(IDPView(idp_id=kitchen.id, category=kitchen.category, viewed_at=at(date(2026, 11, 2))))
    db.session.add(Favourite(customer_id=customer.id, idp_id=kitchen.id, saved_at=at(DAY)))
    db.session.commit()
    return loft, kitchen


# --- PM-08 Daily --------------------------------------------------------------

def test_daily_report_counts_that_day_only(app):
    setup_activity()
    report = GenerateReportController().daily(DAY)
    assert (report.new_accounts, report.new_idps, report.total_views, report.total_shortlists) == (2, 2, 4, 1)


def test_daily_report_ranks_idps_and_categories(app):
    setup_activity()
    report = GenerateReportController().daily(DAY)
    assert report.most_viewed_idps == [("Scandi Loft", "Living Room", 3), ("Teak Kitchen", "Kitchen", 1)]
    assert report.most_shortlisted_idps == [("Teak Kitchen", "Kitchen", 1)]
    assert report.most_viewed_categories == [("Living Room", 3), ("Kitchen", 1)]
    assert report.most_shortlisted_categories == [("Kitchen", 1)]


def test_day_with_no_activity_shows_zeros(app):
    setup_activity()
    report = GenerateReportController().daily(date(2026, 1, 1))
    assert (report.new_accounts, report.new_idps, report.total_views, report.total_shortlists) == (0, 0, 0, 0)
    assert report.most_viewed_idps == []


def test_viewing_a_project_is_logged_for_reports(app):
    loft, _ = setup_activity()
    before = GenerateReportController().daily(date.today()).total_views
    loft.record_view()
    # Compare with the count just before, so the test passes on any date
    assert GenerateReportController().daily(date.today()).total_views == before + 1


def test_daily_figures_match_the_records(app):
    setup_activity()
    assert GenerateReportController().daily(DAY).total_views == IDPView.query.filter(
        IDPView.viewed_at >= at(DAY, 0), IDPView.viewed_at < at(date(2026, 10, 14), 0)).count()


# --- PM-09 Weekly / PM-10 Monthly ---------------------------------------------

def test_weekly_report_totals_monday_to_sunday(app):
    setup_activity()
    report = GenerateReportController().weekly(date(2026, 10, 18))  # Sunday of the same week
    assert report.start == date(2026, 10, 12) and report.end == date(2026, 10, 19)
    assert report.total_views == 5
    assert report.most_viewed_idps[0] == ("Scandi Loft", "Living Room", 3)


def test_monthly_report_totals_the_month(app):
    setup_activity()
    october = GenerateReportController().monthly(2026, 10)
    assert (october.total_views, october.new_accounts) == (5, 2)
    assert GenerateReportController().monthly(2026, 11).total_views == 1


def test_generate_from_page_values(app):
    controller = GenerateReportController()
    assert controller.generate("daily", "2026-10-13").kind == "daily"
    assert controller.generate("weekly", "2026-10-13").start == date(2026, 10, 12)
    assert controller.generate("monthly", "2026-10").end == date(2026, 11, 1)


@pytest.mark.parametrize("kind, value", [("daily", "13/10/2026"), ("monthly", "2026-13"), ("yearly", "2026")])
def test_invalid_report_choices_are_rejected(app, kind, value):
    with pytest.raises(ValueError):
        GenerateReportController().generate(kind, value)


# --- PM-11 Download -----------------------------------------------------------

@pytest.mark.parametrize("kind, value, expected", [
    ("daily", "2026-10-13", "daily_report_2026-10-13"),
    ("weekly", "2026-10-15", "weekly_report_2026-10-12"),
    ("monthly", "2026-10", "monthly_report_2026-10"),
])
def test_file_name_has_report_type_and_date(app, kind, value, expected):
    report = GenerateReportController().generate(kind, value)
    assert DownloadReportController().download(report, "xlsx")[0] == f"{expected}.xlsx"
    assert DownloadReportController().download(report, "pdf")[0] == f"{expected}.pdf"


def workbook(report):
    _, content_type, data = DownloadReportController().download(report, "xlsx")
    assert content_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return load_workbook(io.BytesIO(data))


def rows(sheet):
    return [[cell for cell in row] for row in sheet.iter_rows(values_only=True)]


def test_excel_has_the_same_figures_as_the_report(app):
    setup_activity()
    book = workbook(GenerateReportController().daily(DAY))
    assert book.sheetnames == ["Summary", "Activity", "Top lists"]
    summary = rows(book["Summary"])
    assert ["Total IDP views", 4, 0, "new"] in summary and ["New user accounts", 2, 0, "new"] in summary
    assert [1, "Scandi Loft", "Living Room", 3] in rows(book["Top lists"])


def test_pdf_is_a_valid_pdf_with_the_figures(app):
    setup_activity()
    report = GenerateReportController().daily(DAY)
    _, content_type, data = DownloadReportController().download(report, "pdf")
    assert content_type == "application/pdf"
    assert data.startswith(b"%PDF-") and data.rstrip().endswith(b"%%EOF")
    assert b"(Total IDP views) Tj" in data and b"(4) Tj" in data and b"Scandi Loft" in data


def test_unknown_download_format_is_rejected(app):
    with pytest.raises(ValueError, match="PDF or Excel"):
        DownloadReportController().download(GenerateReportController().daily(DAY), "csv")


def test_excel_does_not_let_a_project_title_run_as_a_formula(app):
    designer = UserAccount.create("des@test.com", "password123", "designer", name="Des")
    evil = IDP(title='=HYPERLINK("http://evil","x")', category="Kitchen", designer_id=designer.id)
    db.session.add(evil)
    db.session.commit()
    db.session.add(IDPView(idp_id=evil.id, category="Kitchen", viewed_at=datetime.now()))
    db.session.commit()
    sheet = workbook(GenerateReportController().daily(date.today()))["Top lists"]
    cells = [cell for row in sheet.iter_rows() for cell in row if cell.value == evil.title]
    assert cells and all(cell.data_type == "s" for cell in cells)  # stored as text, not a formula


# --- Report enhancements: previous period, enquiries, activity in the downloads ---------

def test_previous_period_is_the_day_week_or_month_before(app):
    controller = GenerateReportController()
    assert controller.daily(DAY).previous().start == date(2026, 10, 12)
    assert controller.weekly(DAY).previous().start == date(2026, 10, 5)
    march = controller.monthly(2026, 3).previous()
    assert (march.start, march.end) == (date(2026, 2, 1), date(2026, 3, 1))
    assert controller.monthly(2026, 1).previous().start == date(2025, 12, 1)


def test_comparison_shows_change_against_previous_period(app):
    setup_activity()  # 15 Oct has 1 view; 13 Oct has 4 views
    loft = IDP.query.filter_by(title="Scandi Loft").one()
    db.session.add(IDPView(idp_id=loft.id, category=loft.category, viewed_at=at(date(2026, 10, 14))))
    db.session.add(IDPView(idp_id=loft.id, category=loft.category, viewed_at=at(date(2026, 10, 14), 13)))
    db.session.commit()
    rows = {r["label"]: r for r in GenerateReportController().daily(date(2026, 10, 14)).comparison()}
    assert (rows["Total IDP views"]["value"], rows["Total IDP views"]["previous"]) == (2, 4)
    assert rows["Total IDP views"]["change"] == -50
    assert rows["New IDPs"]["change"] is None or rows["New IDPs"]["previous"] == 2
    first_day = {r["label"]: r for r in GenerateReportController().daily(DAY).comparison()}
    assert first_day["Total IDP views"]["change"] == "new"
    assert ActivityReport.change_text(-50) == "-50%" and ActivityReport.change_text(None) == "-"


def test_report_counts_new_enquiries(app):
    from app.entity.enquiry import Enquiry

    loft, _ = setup_activity()
    customer = UserAccount.query.filter_by(email="cus@test.com").one()
    db.session.add(Enquiry(designer_id=loft.designer_id, customer_id=customer.id, idp_id=loft.id,
                           name="Cus", contact="cus@test.com", message="Hi", created_at=at(DAY)))
    db.session.commit()
    report = GenerateReportController().daily(DAY)
    assert report.new_enquiries == 1 and ("New enquiries", 1) in report.summary_rows()


def test_excel_has_activity_per_hour_with_a_total(app):
    setup_activity()  # 13 Oct: views at 0:00, 9:00, 12:00 and 23:00, 1 shortlist at 12:00
    activity = rows(workbook(GenerateReportController().daily(DAY))["Activity"])
    assert ["Hour", "IDP views", "Shortlists"] in activity
    by_hour = {row[0]: row[1:3] for row in activity if isinstance(row[0], datetime)}  # real Excel dates
    assert by_hour[datetime(2026, 10, 13, 9)] == [1, 0] and by_hour[datetime(2026, 10, 13, 12)] == [1, 1]
    assert len(by_hour) == 24
    assert ["Total", "=SUM(B5:B28)", "=SUM(C5:C28)"] == activity[28][:3]


def test_excel_has_charts_made_from_the_figures(app):
    setup_activity()
    book = workbook(GenerateReportController().weekly(DAY))
    assert [type(c).__name__ for c in book["Summary"]._charts] == ["BarChart"]
    assert [type(c).__name__ for c in book["Activity"]._charts] == ["LineChart"]
    assert len(book["Top lists"]._charts) == 4  # one bar chart per ranked list
    line = book["Activity"]._charts[0]
    assert len(line.series) == 2  # views and shortlists


def test_pdf_has_chart_and_page_numbers(app):
    setup_activity()
    _, _, data = DownloadReportController().download(GenerateReportController().weekly(DAY), "pdf")
    assert b"(Views and shortlists per day) Tj" in data
    assert b"(Page 1 of " in data
    assert b"(-75%) Tj" not in data  # previous week had no activity, so changes read "new"
    assert b"(new) Tj" in data
