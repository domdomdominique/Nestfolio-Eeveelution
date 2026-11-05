"""A very small PDF writer for reports, so no extra package is needed.

PdfCanvas draws A4 pages with Helvetica text, lines, filled shapes and simple tables;
build_pdf(lines) is the plain version that writes left-aligned lines of (text, bold).
"""

PAGE_WIDTH, PAGE_HEIGHT = 595, 842  # A4 in points
MARGIN, LINE_HEIGHT, FONT_SIZE = 56, 16, 11
LINES_PER_PAGE = (PAGE_HEIGHT - 2 * MARGIN) // LINE_HEIGHT

# Helvetica character widths (per 1000 points of font size) for ASCII 32 to 126, from the
# standard font metrics, so text can be right-aligned and long names shortened to fit.
_WIDTHS = [
    278, 278, 355, 556, 556, 889, 667, 191, 333, 333, 389, 584, 278, 333, 278, 278,
    556, 556, 556, 556, 556, 556, 556, 556, 556, 556, 278, 278, 584, 584, 584, 556,
    1015, 667, 667, 722, 722, 667, 611, 778, 722, 278, 500, 667, 556, 833, 722, 778,
    667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611, 278, 278, 278, 469, 556,
    333, 556, 556, 500, 556, 556, 278, 556, 556, 222, 222, 500, 222, 833, 556, 556,
    556, 556, 333, 500, 278, 556, 500, 722, 500, 500, 500, 334, 260, 334, 584,
]


def _escape(text):
    text = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    return text.encode("cp1252", "replace").decode("latin-1")


def text_width(text, size, bold=False):
    units = sum(_WIDTHS[ord(c) - 32] if 32 <= ord(c) <= 126 else 556 for c in text)
    return units * size / 1000 * (1.1 if bold else 1)


def fit(text, width, size, bold=False):
    """text, shortened with '...' if it is wider than width."""
    if text_width(text, size, bold) <= width:
        return text
    while text and text_width(text + "...", size, bold) > width:
        text = text[:-1]
    return text.rstrip() + "..."


def _colour(hex_colour):
    hex_colour = hex_colour.lstrip("#")
    return " ".join(f"{int(hex_colour[i:i + 2], 16) / 255:.3f}" for i in (0, 2, 4))


class PdfCanvas:
    """Draws on A4 pages. y is measured from the top of the page, like a web page."""

    def __init__(self, margin=48):
        self.margin = margin
        self.pages = []
        self.y = 0
        self.new_page()

    @property
    def width(self):
        return PAGE_WIDTH - 2 * self.margin

    def new_page(self):
        self.pages.append([])
        self.y = self.margin

    def need(self, height, bottom_space=40):
        """Start a new page unless height more points fit above the footer."""
        if self.y + height > PAGE_HEIGHT - self.margin - bottom_space:
            self.new_page()

    # --- Drawing ----------------------------------------------------------------------

    def _ops(self):
        return self.pages[-1]

    def text(self, x, y, text, size=10, bold=False, colour="#2b2118", align="left", page=None):
        if align == "right":
            x -= text_width(text, size, bold)
        elif align == "center":
            x -= text_width(text, size, bold) / 2
        ops = self.pages[page] if page is not None else self._ops()
        ops.append(f"BT /F{2 if bold else 1} {size} Tf {_colour(colour)} rg "
                   f"{x:.1f} {PAGE_HEIGHT - y:.1f} Td ({_escape(text)}) Tj ET")

    def line(self, x1, y1, x2, y2, colour="#d9cfc6", width=0.8, page=None):
        ops = self.pages[page] if page is not None else self._ops()
        ops.append(f"{_colour(colour)} RG {width} w {x1:.1f} {PAGE_HEIGHT - y1:.1f} m "
                   f"{x2:.1f} {PAGE_HEIGHT - y2:.1f} l S")

    def rect(self, x, y, w, h, fill):
        self._ops().append(f"{_colour(fill)} rg {x:.1f} {PAGE_HEIGHT - y - h:.1f} {w:.1f} {h:.1f} re f")

    def polyline(self, points, colour, width=1.6):
        if len(points) < 2:
            return
        path = " ".join(f"{x:.1f} {PAGE_HEIGHT - y:.1f} {'m' if i == 0 else 'l'}"
                        for i, (x, y) in enumerate(points))
        self._ops().append(f"{_colour(colour)} RG {width} w 1 j 1 J {path} S")

    def polygon(self, points, fill):
        path = " ".join(f"{x:.1f} {PAGE_HEIGHT - y:.1f} {'m' if i == 0 else 'l'}"
                        for i, (x, y) in enumerate(points))
        self._ops().append(f"{_colour(fill)} rg {path} h f")

    def dot(self, x, y, radius, fill):
        k = radius * 0.5523  # four Bezier curves make a circle
        y = PAGE_HEIGHT - y
        self._ops().append(
            f"{_colour(fill)} rg {x + radius:.1f} {y:.1f} m "
            f"{x + radius:.1f} {y + k:.1f} {x + k:.1f} {y + radius:.1f} {x:.1f} {y + radius:.1f} c "
            f"{x - k:.1f} {y + radius:.1f} {x - radius:.1f} {y + k:.1f} {x - radius:.1f} {y:.1f} c "
            f"{x - radius:.1f} {y - k:.1f} {x - k:.1f} {y - radius:.1f} {x:.1f} {y - radius:.1f} c "
            f"{x + k:.1f} {y - radius:.1f} {x + radius:.1f} {y - k:.1f} {x + radius:.1f} {y:.1f} c f")

    # --- Building blocks --------------------------------------------------------------

    def heading(self, text, size=13, keep_with=40):
        """A section heading; keep_with is how much of what follows must fit on the same page,
        so a heading is never left alone at the bottom of a page."""
        self.need(size + 16 + keep_with)
        self.y += size + 6
        self.text(self.margin, self.y, text, size=size, bold=True, colour="#3b2a1b")
        self.y += 10

    def table(self, columns, rows, widths, numeric=(), empty="No activity."):
        """A table with a shaded header row; columns listed in numeric are right-aligned."""
        left, row_h, size = self.margin, 18, 9.5
        xs = [left]
        for w in widths[:-1]:
            xs.append(xs[-1] + w)

        def cell_x(i):
            return xs[i] + widths[i] - 6 if i in numeric else xs[i] + 6

        def header():
            self.rect(left, self.y, sum(widths), row_h, "#f1e9e1")
            for i, name in enumerate(columns):
                self.text(cell_x(i), self.y + 12.5, name, size=size, bold=True, colour="#5b4a3c",
                          align="right" if i in numeric else "left")
            self.y += row_h

        self.need(row_h * 2)
        header()
        if not rows:
            self.text(left + 6, self.y + 13, empty, size=size, colour="#7a6a5d")
            self.y += row_h
        for row in rows:
            if self.y + row_h > PAGE_HEIGHT - self.margin - 40:
                self.new_page()
                header()
            for i, cell in enumerate(row):
                value = f"{cell:,}" if isinstance(cell, int) else str(cell)
                self.text(cell_x(i), self.y + 12.5, fit(value, widths[i] - 12, size), size=size,
                          align="right" if i in numeric else "left")
            self.y += row_h
            self.line(left, self.y, left + sum(widths), self.y, colour="#ece4dc", width=0.6)
        self.y += 6

    CHART_HEIGHT = 170

    def line_chart(self, labels, series, height=CHART_HEIGHT):
        """series is [(name, colour, values)]; None values (still to come) are left out."""
        self.need(height + 40)
        left, right = self.margin + 34, self.margin + self.width - 6
        top, base = self.y + 22, self.y + height - 20
        known = [v for _, _, values in series for v in values if v is not None]
        step = _nice_step(max(known) if known else 0)
        peak = step * 4
        count = len(labels)

        def px(i):
            return left + ((right - left) * i / (count - 1) if count > 1 else (right - left) / 2)

        def py(v):
            return base - (base - top) * v / peak

        x = self.margin  # legend
        for name, colour, _ in series:
            self.rect(x, self.y + 4, 10, 10, colour)
            self.text(x + 14, self.y + 13, name, size=9, colour="#5b4a3c")
            x += 24 + text_width(name, 9)
        for k in range(5):
            value = step * k
            self.line(left, py(value), right, py(value), colour="#ece4dc" if k else "#b9aba0")
            self.text(left - 6, py(value) + 3, f"{value:,}", size=8, colour="#7a6a5d", align="right")
        every = max(1, -(-count // 8))
        for i in range(0, count, every):
            self.text(px(i), base + 13, labels[i], size=8, colour="#7a6a5d", align="center")
        for _, colour, values in series:
            points = [(px(i), py(v)) for i, v in enumerate(values) if v is not None]
            self.polyline(points, colour)
            if count <= 40:
                for point in points:
                    self.dot(*point, 1.8, colour)
        self.y += height + 6

    def footer(self, left_text):
        total = len(self.pages)
        for n in range(total):
            y = PAGE_HEIGHT - self.margin + 18
            self.line(self.margin, y - 12, self.margin + self.width, y - 12, page=n)
            self.text(self.margin, y, left_text, size=8, colour="#7a6a5d", page=n)
            self.text(self.margin + self.width, y, f"Page {n + 1} of {total}", size=8,
                      colour="#7a6a5d", align="right", page=n)

    def to_bytes(self):
        return _write(self.pages)


def _nice_step(value):
    """Step between 4 grid lines: 1, 2, 3 or 5 times a power of ten (matches the web charts)."""
    needed, power = max(value, 1) / 4, 1
    while True:
        for step in (1, 2, 3, 5):
            if step * power >= needed:
                return step * power
        power *= 10


def build_pdf(lines):
    """Plain A4 pages of left-aligned text; each line is (text, bold)."""
    pages = [lines[i:i + LINES_PER_PAGE] for i in range(0, len(lines), LINES_PER_PAGE)] or [[]]
    contents = []
    for page_lines in pages:
        ops = ["BT", f"{MARGIN} {PAGE_HEIGHT - MARGIN} Td", f"{LINE_HEIGHT} TL"]
        for text, is_bold in page_lines:
            ops.append(f"/F{2 if is_bold else 1} {FONT_SIZE} Tf ({_escape(text)}) Tj T*")
        ops.append("ET")
        contents.append(ops)
    return _write(contents)


def _write(pages):
    """The PDF file for a list of pages, each a list of content-stream operators."""
    objects = []  # object bodies, numbered from 1

    def add(body):
        objects.append(body)
        return len(objects)

    catalog = add(None)
    pages_obj = add(None)
    regular = add("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
    bold = add("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>")
    page_ids = []
    for ops in pages or [[]]:
        stream = "\n".join(ops).encode("latin-1")
        content = add(f"<< /Length {len(stream)} >>\nstream\n".encode("latin-1") + stream + b"\nendstream")
        page_ids.append(add(
            f"<< /Type /Page /Parent {pages_obj} 0 R /MediaBox [0 0 {PAGE_WIDTH} {PAGE_HEIGHT}] "
            f"/Resources << /Font << /F1 {regular} 0 R /F2 {bold} 0 R >> >> /Contents {content} 0 R >>"))
    objects[catalog - 1] = f"<< /Type /Catalog /Pages {pages_obj} 0 R >>"
    kids = " ".join(f"{pid} 0 R" for pid in page_ids)
    objects[pages_obj - 1] = f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>"

    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        body = body if isinstance(body, bytes) else body.encode("latin-1")
        out += f"{number} 0 obj\n".encode() + body + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    out += "".join(f"{offset:010d} 00000 n \n" for offset in offsets).encode()
    out += f"trailer\n<< /Size {len(objects) + 1} /Root {catalog} 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return bytes(out)
