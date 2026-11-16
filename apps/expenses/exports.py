"""Building the CSV and PDF export files (kept out of the view so they can be tested alone)."""

import csv
from decimal import Decimal

from fpdf import FPDF

CSV_HEADER = ["ID", "Date", "Category", "Amount", "Description"]
PDF_MAX_ROWS = 5000  # a PDF is built in memory, so very large exports are refused (CSV streams instead)


def _csv_safe(text):
    """
    Defuse "CSV injection": a cell starting with = + - or @ is run as a formula by Excel/Sheets
    (e.g. a description of =HYPERLINK(...)). Prefixing a quote makes it plain text.
    """
    if text and text[0] in "=+-@\t\r":
        return "'" + text
    return text


class _Echo:
    """A file-like object whose write() just returns the value, so csv.writer can feed a generator."""

    def write(self, value):
        return value


def iter_csv(expenses):
    """
    Yield the CSV file line by line.

    Used with StreamingHttpResponse: the response is sent while it is being generated, and
    `.iterator()` reads rows from the database in chunks, so memory stays flat even for huge exports.
    """
    writer = csv.writer(_Echo())
    yield writer.writerow(CSV_HEADER)
    for expense in expenses.iterator():
        yield writer.writerow(
            [
                expense.id,
                expense.date.isoformat(),
                expense.category,
                expense.amount,
                _csv_safe(expense.description),
            ]
        )


def _latin1(text):
    """
    fpdf2's built-in fonts only support Latin-1; any other character (₹, Hindi, emoji) would raise
    an error. Replace unsupported characters with "?" instead of failing the whole export.
    """
    return text.encode("latin-1", "replace").decode("latin-1")


def build_expenses_pdf(expenses, username, from_date=None, to_date=None, generated_at=None):
    """Return the PDF bytes for a list of expenses (already loaded, newest first)."""
    col_widths = [20, 28, 35, 28, 79]
    headers = ["#", "Date", "Category", "Amount", "Description"]
    total = sum((e.amount for e in expenses), Decimal("0"))

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Expense Report", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_font("Helvetica", size=10)
    stamp = generated_at.strftime("%Y-%m-%d %H:%M") if generated_at else ""
    pdf.cell(
        0, 8, _latin1(f"Generated: {stamp}  |  User: {username}"), new_x="LMARGIN", new_y="NEXT", align="C"
    )
    if from_date or to_date:
        pdf.cell(
            0,
            6,
            f"Period: {from_date or 'start'} to {to_date or 'today'}",
            new_x="LMARGIN",
            new_y="NEXT",
            align="C",
        )
    pdf.ln(4)

    def table_header():
        pdf.set_fill_color(67, 97, 238)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "B", 10)
        for width, title in zip(col_widths, headers, strict=True):
            pdf.cell(width, 8, title, border=1, fill=True)
        pdf.ln()
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Helvetica", size=9)

    table_header()
    for index, expense in enumerate(expenses):
        if pdf.will_page_break(7):  # repeat the table header on every new page
            pdf.add_page()
            table_header()
        pdf.set_fill_color(240, 240, 255) if index % 2 == 0 else pdf.set_fill_color(255, 255, 255)
        row = [
            str(expense.id),
            expense.date.isoformat(),
            expense.category,
            f"${expense.amount:.2f}",
            _latin1(expense.description[:45]),
        ]
        for width, value in zip(col_widths, row, strict=True):
            pdf.cell(width, 7, value, border=1, fill=True)
        pdf.ln()

    pdf.set_font("Helvetica", "B", 10)
    pdf.set_fill_color(230, 230, 255)
    pdf.cell(sum(col_widths[:3]), 8, "TOTAL", border=1, fill=True)
    pdf.cell(col_widths[3], 8, f"${total:.2f}", border=1, fill=True)
    pdf.cell(col_widths[4], 8, f"{len(expenses)} expense(s)", border=1, fill=True)
    pdf.ln()
    return bytes(pdf.output())
