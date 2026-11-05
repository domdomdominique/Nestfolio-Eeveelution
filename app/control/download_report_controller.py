import io
from datetime import datetime

from openpyxl import Workbook
from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from app.control.simple_pdf import PdfCanvas

XLSX_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

# Nestfolio colours, as in the PDF and the charts on the Reports page
ESPRESSO, TAN, PALE, DARK, MUTED = "664930", "C58B5C", "D9C3AE", "2B2118", "7A6A5D"
HEADER_FILL = PatternFill("solid", fgColor="F1E9E1")
RULE = Border(bottom=Side(style="thin", color="E4DAD0"))
RANKING_BLOCK = 18  # rows per ranked list on the "Top lists" sheet, so each chart sits beside its table


class DownloadReportController:
    """Control: handles the Platform Management 'Download report as PDF or Excel'
    use case (PM-11). Both files hold the same figures as the report on screen;
    the Excel workbook also has native Excel charts drawn from those figures.

    download() returns (file name, content type, bytes) for the boundary to send.
    """

    FORMATS = ("xlsx", "pdf")

    def download(self, report, file_format):
        if file_format not in self.FORMATS:
            raise ValueError("Please choose PDF or Excel.")
        if file_format == "xlsx":
            return f"{report.file_stem}.xlsx", XLSX_TYPE, self.to_xlsx(report)
        return f"{report.file_stem}.pdf", "application/pdf", self.to_pdf(report)

    # --- Excel -----------------------------------------------------------------------------

    def to_xlsx(self, report):
        """Three sheets: Summary (with a bar chart against the previous period), Activity
        (views and shortlists per hour or day, with a line chart) and Top lists (each ranked
        list with a bar chart)."""
        book = Workbook()
        self._summary_sheet(book.active, report)
        self._activity_sheet(book.create_sheet("Activity"), report)
        self._rankings_sheet(book.create_sheet("Top lists"), report)
        buffer = io.BytesIO()
        book.save(buffer)
        return buffer.getvalue()

    @staticmethod
    def _put(sheet, row, column, value, **style):
        """Write one cell. Text is always stored as plain text, so a project title like
        =HYPERLINK(...) can never run as a formula when the file is opened."""
        cell = sheet.cell(row=row, column=column, value=value)
        if isinstance(value, str):
            cell.data_type = "s"
        for name, setting in style.items():
            setattr(cell, name, setting)
        return cell

    def _title(self, sheet, report, subtitle):
        self._put(sheet, 1, 1, report.title, font=Font(size=16, bold=True, color=DARK))
        self._put(sheet, 2, 1, f"{subtitle}  |  Generated {report.generated_at:%d %b %Y, %H:%M}",
                  font=Font(size=9, color=MUTED))

    def _table(self, sheet, row, headings, rows, number_formats):
        """A table starting in column A with a shaded header row; returns its last row."""
        for column, heading in enumerate(headings, start=1):
            self._put(sheet, row, column, heading, font=Font(bold=True, color=ESPRESSO),
                      fill=HEADER_FILL, border=RULE,
                      alignment=Alignment(horizontal="left" if column == 1 else "right"))
        for r, values in enumerate(rows, start=row + 1):
            for column, value in enumerate(values, start=1):
                cell = self._put(sheet, r, column, value, border=RULE)
                if column in number_formats and isinstance(value, (int, float)):
                    cell.number_format = number_formats[column]
                if column > 1 and not isinstance(value, str) or column in number_formats:
                    cell.alignment = Alignment(horizontal="right")
        return row + len(rows)

    @staticmethod
    def _widths(sheet, widths):
        for index, width in enumerate(widths, start=1):
            sheet.column_dimensions[get_column_letter(index)].width = width

    @staticmethod
    def _chart(chart, sheet, anchor, title, colours, size, legend=True):
        chart.title = title
        chart.title.overlay = False  # title above the plot, not on top of it
        chart.width, chart.height = size
        chart.x_axis.delete = chart.y_axis.delete = False  # newer Excel hides the axes otherwise
        if legend:
            chart.legend.position = "t"
            chart.legend.overlay = False
        else:
            chart.legend = None
        if isinstance(chart, BarChart) and chart.type == "bar":
            # Listed top to bottom like the table, with the number axis kept at the bottom
            chart.x_axis.scaling.orientation = "maxMin"
            chart.y_axis.crosses = "max"
        for series, colour in zip(chart.series, colours):
            series.graphicalProperties.line.solidFill = colour
            if isinstance(chart, BarChart):
                series.graphicalProperties.solidFill = colour
            else:
                series.graphicalProperties.line.width = 22000  # EMU, about 1.75 pt
                series.smooth = False
        sheet.add_chart(chart, anchor)

    def _summary_sheet(self, sheet, report):
        sheet.title = "Summary"
        period = report.period_name
        self._title(sheet, report, f"Compared with the previous {period}")
        rows = []
        for row in report.comparison():
            change = row["change"]
            # A real percentage, so it can be sorted and charted; text when there is nothing to compare
            change = change / 100 if isinstance(change, int) else ("new" if change == "new" else "-")
            rows.append([row["label"], row["value"], row["previous"], change])
        last = self._table(sheet, 4, ["Figure", f"This {period}", f"Previous {period}", "Change"], rows,
                           {2: "#,##0", 3: "#,##0", 4: "+0%;-0%;0%"})
        self._widths(sheet, [24, 14, 16, 10])
        sheet.freeze_panes = "A5"

        chart = BarChart()
        chart.type = "bar"  # horizontal bars keep the figure names readable
        chart.add_data(Reference(sheet, min_col=2, max_col=3, min_row=4, max_row=last), titles_from_data=True)
        chart.set_categories(Reference(sheet, min_col=1, min_row=5, max_row=last))
        self._chart(chart, sheet, "F4", f"This {period} compared with the previous {period}",
                    [ESPRESSO, PALE], (20, 9))

    def _activity_sheet(self, sheet, report):
        timeline = report.timeline()
        unit = timeline.unit
        self._title(sheet, report, f"IDP views and shortlists per {unit}")
        # Real Excel dates (not text), so the column can be sorted, filtered and charted by date
        key_format = "%Y-%m-%d %H" if unit == "hour" else "%Y-%m-%d"
        rows = [[datetime.strptime(key, key_format) if unit == "hour"
                 else datetime.strptime(key, key_format).date(), views, saves]
                for key, views, saves in zip(timeline.keys, timeline.views, timeline.shortlists)
                if views is not None]  # leave out hours or days that have not happened yet
        last = self._table(sheet, 4, ["Hour" if unit == "hour" else "Date", "IDP views", "Shortlists"],
                           rows, {2: "#,##0", 3: "#,##0"})
        date_format = "dd mmm yyyy hh:mm" if unit == "hour" else "ddd dd mmm yyyy"
        for r in range(5, 5 + len(rows)):
            sheet.cell(row=r, column=1).number_format = date_format
            sheet.cell(row=r, column=1).alignment = Alignment(horizontal="left")
        self._widths(sheet, [20, 12, 12])
        sheet.freeze_panes = "A5"
        if not rows:
            self._put(sheet, 5, 1, "This period has not started yet.", font=Font(italic=True, color=MUTED))
            return
        self._put(sheet, last + 1, 1, "Total", font=Font(bold=True))
        for column in (2, 3):
            letter = get_column_letter(column)
            total = sheet.cell(row=last + 1, column=column, value=f"=SUM({letter}5:{letter}{last})")
            total.font, total.number_format = Font(bold=True), "#,##0"

        chart = LineChart()
        chart.add_data(Reference(sheet, min_col=2, max_col=3, min_row=4, max_row=last), titles_from_data=True)
        chart.set_categories(Reference(sheet, min_col=1, min_row=5, max_row=last))
        chart.x_axis.number_format = "hh:mm" if unit == "hour" else "dd mmm"
        chart.x_axis.tickLblSkip = max(1, -(-len(rows) // 12))  # about 12 labels, like the web chart
        chart.x_axis.tickMarkSkip = chart.x_axis.tickLblSkip
        chart.x_axis.auto = False  # one point per row; Excel would otherwise merge the hours of a day
        self._chart(chart, sheet, "E4", f"IDP views and shortlists per {unit}", [ESPRESSO, TAN], (26, 12))

    def _rankings_sheet(self, sheet, report):
        self._title(sheet, report, f"Top {report.TOP_N} for the {report.period_name}")
        row = 4
        for heading, columns, rows in report.sections():
            self._put(sheet, row, 1, heading, font=Font(size=12, bold=True, color=DARK))
            count_col = len(columns) + 1  # rank, the name columns, then the count
            last = self._table(sheet, row + 1, ["#", *columns],
                               [[n, *values] for n, values in enumerate(rows, start=1)],
                               {count_col: "#,##0"})
            if rows:
                chart = BarChart()
                chart.type = "bar"
                chart.add_data(Reference(sheet, min_col=count_col, min_row=row + 1, max_row=last),
                               titles_from_data=True)
                chart.set_categories(Reference(sheet, min_col=2, min_row=row + 2, max_row=last))
                self._chart(chart, sheet, f"F{row}", heading, [ESPRESSO], (17, 7.5), legend=False)
            else:
                self._put(sheet, row + 2, 1, "No activity.", font=Font(italic=True, color=MUTED))
            row += RANKING_BLOCK
        self._widths(sheet, [5, 46, 16, 12])

    # --- PDF -------------------------------------------------------------------------------

    def to_pdf(self, report):
        pdf = PdfCanvas()
        left, width = pdf.margin, pdf.width

        # Title block
        pdf.text(left, pdf.y + 10, "NESTFOLIO  |  PLATFORM REPORT", size=8, bold=True, colour="#664930")
        pdf.text(left, pdf.y + 34, report.title, size=20, bold=True, colour="#2b2118")
        pdf.text(left, pdf.y + 52, f"Generated {report.generated_at:%d %b %Y, %H:%M}", size=9, colour="#7a6a5d")
        pdf.y += 64
        pdf.line(left, pdf.y, left + width, pdf.y, colour="#664930", width=1.2)
        pdf.y += 8

        # Summary, with the change since the previous period
        period = report.period_name
        pdf.heading("Summary")
        pdf.table(["Figure", f"This {period}", f"Previous {period}", "Change"],
                  [[row["label"], row["value"], row["previous"], report.change_text(row["change"])]
                   for row in report.comparison()],
                  [width - 270, 90, 100, 80], numeric=(1, 2, 3))

        # Views and shortlists over the period
        timeline = report.timeline()
        pdf.heading(f"Views and shortlists per {timeline.unit}", keep_with=pdf.CHART_HEIGHT + 6)
        pdf.line_chart(timeline.labels, [("IDP views", "#664930", timeline.views),
                                         ("Shortlists", "#c58b5c", timeline.shortlists)])

        # Ranked lists
        for heading, columns, rows in report.sections():
            pdf.heading(heading)
            if len(columns) == 3:   # IDP, Category, count
                widths = [30, width - 30 - 140 - 80, 140, 80]
            else:                   # Category, count
                widths = [30, width - 30 - 80, 80]
            pdf.table(["#", *columns], [[n, *row] for n, row in enumerate(rows, start=1)],
                      widths, numeric=(0, len(columns)))

        pdf.footer(f"Nestfolio - {report.title}")
        return pdf.to_bytes()
