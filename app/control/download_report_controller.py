import csv
import io

from app.control.simple_pdf import build_pdf


def safe_cell(value):
    """Stop a title like =HYPERLINK(...) running as a formula when the CSV is opened in Excel."""
    if isinstance(value, str) and value[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + value
    return value


class DownloadReportController:
    """Control: handles the Platform Management 'Download report as PDF or CSV'
    use case (PM-11). Both files hold the same figures as the report on screen.

    download() returns (file name, content type, bytes) for the boundary to send.
    """

    FORMATS = ("csv", "pdf")

    def download(self, report, file_format):
        if file_format not in self.FORMATS:
            raise ValueError("Please choose PDF or CSV.")
        if file_format == "csv":
            return f"{report.file_stem}.csv", "text/csv", self.to_csv(report)
        return f"{report.file_stem}.pdf", "application/pdf", self.to_pdf(report)

    def to_csv(self, report):
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow([report.title])
        writer.writerow(["Generated", report.generated_at.strftime("%Y-%m-%d %H:%M")])
        writer.writerow([])
        writer.writerow(["Figure", "Value"])
        writer.writerows(report.summary_rows())
        for heading, columns, rows in report.sections():
            writer.writerow([])
            writer.writerow([heading])
            writer.writerow(columns)
            writer.writerows([safe_cell(cell) for cell in row] for row in rows)
        return buffer.getvalue().encode("utf-8-sig")  # BOM so Excel shows symbols correctly

    def to_pdf(self, report):
        lines = [(report.title, True),
                 (f"Generated {report.generated_at:%d %b %Y, %H:%M}", False), ("", False)]
        lines += [(f"{label}: {value}", False) for label, value in report.summary_rows()]
        for heading, _, rows in report.sections():
            lines += [("", False), (heading, True)]
            if not rows:
                lines.append(("No activity.", False))
            for n, row in enumerate(rows, start=1):
                *names, count = row
                lines.append((f"{n}. {' - '.join(names)}: {count}", False))
        return build_pdf(lines)
