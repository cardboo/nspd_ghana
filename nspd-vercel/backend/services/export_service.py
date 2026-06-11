"""
CSV and PDF export generation.

CSV: converted from api/export-all-csv.php (same columns, same UTF-8 BOM
for Excel, same date format).

PDF: converted from api/export-pdf.php. TCPDF is PHP-only and HTML-to-PDF
engines need native binaries that Vercel's Python runtime doesn't ship, so
the report is rebuilt with fpdf2 (pure Python) reproducing the same layout:
navy title banner, blue section bars, bordered label/value rows, and
green/red Yes/No badges.
"""

import csv
import io
import math
from datetime import datetime

from fpdf import FPDF
from fpdf.enums import XPos, YPos

CSV_HEADERS = [
    "ID", "Surname", "First Name", "Other Names", "Telephone", "Email",
    "Position/Rank", "Short Courses (RMU)", "ISPS/GMA Familiarisation",
    "Attachment", "Medicals", "Sea Experience", "Total Sea Experience (Years)",
    "Last Ship Type", "Status", "Submitted Date",
]

# Colours from the original TCPDF HTML template
NAVY = (0, 61, 107)        # #003d6b
SECTION_BLUE = (0, 102, 179)  # #0066b3
BORDER_GREY = (204, 204, 204)
LABEL_GREY = (102, 102, 102)
TEXT_DARK = (51, 51, 51)
FOOTER_GREY = (136, 136, 136)
GREEN_BG, GREEN_TEXT = (212, 237, 218), (21, 87, 36)
RED_BG, RED_TEXT = (248, 215, 218), (114, 28, 33)


def _php_long_datetime(value) -> str:
    """PHP date('F d, Y \\a\\t g:i A') -> 'January 05, 2026 at 3:04 PM'."""
    if not value:
        return ""
    hour = value.strftime("%I").lstrip("0") or "12"
    return value.strftime("%B %d, %Y") + " at " + hour + value.strftime(":%M %p")


def _php_csv_datetime(value) -> str:
    """PHP date('F d, Y H:i:s') -> 'January 05, 2026 22:40:37'."""
    return value.strftime("%B %d, %Y %H:%M:%S") if value else ""


def generate_csv(applications) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(CSV_HEADERS)
    for app in applications:
        writer.writerow([
            app.id,
            app.surname,
            app.first_name,
            app.other_names or "",
            app.telephone,
            app.email,
            app.position_rank,
            app.short_courses_rmu,
            app.familiarisation_isps_gma,
            app.attachment or "",
            app.medicals or "",
            app.sea_experience or "",
            app.total_sea_experience_years if app.total_sea_experience_years is not None else "",
            app.last_ship_type or "",
            app.status or "Pending",
            _php_csv_datetime(app.submitted_at),
        ])
    # BOM for Excel UTF-8 support (same as the PHP version)
    return "\ufeff" + buffer.getvalue()


def _latin1(value: str) -> str:
    """fpdf2 core fonts are latin-1; replace anything outside it."""
    return str(value or "").encode("latin-1", "replace").decode("latin-1")


def generate_submission_pdf(app) -> bytes:
    pdf = FPDF()
    pdf.set_margins(15, 15, 15)
    pdf.set_auto_page_break(True, margin=15)
    pdf.add_page()

    # Title banner
    pdf.set_fill_color(*NAVY)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("helvetica", "B", 15)
    pdf.cell(0, 14, "NSPD Ghana - Submission Details Report",
             align="C", fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def section_title(title: str) -> None:
        pdf.ln(6)
        pdf.set_fill_color(*SECTION_BLUE)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("helvetica", "B", 11)
        pdf.cell(0, 8, title, fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(2)

    def row(label: str, value: str, text_color=TEXT_DARK, fill_color=None) -> None:
        pdf.set_draw_color(*BORDER_GREY)
        pdf.set_font("helvetica", "B", 9)
        pdf.set_text_color(*LABEL_GREY)
        pdf.cell(55, 7, _latin1(label), border=1)
        pdf.set_font("helvetica", "", 10)
        pdf.set_text_color(*text_color)
        if fill_color:
            pdf.set_fill_color(*fill_color)
        pdf.cell(0, 7, _latin1(value), border=1, fill=bool(fill_color),
                 new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def badge_row(label: str, value) -> None:
        if value == "Yes":
            row(label, "Yes", text_color=GREEN_TEXT, fill_color=GREEN_BG)
        else:
            row(label, "No", text_color=RED_TEXT, fill_color=RED_BG)

    section_title("Personal Information")
    row("Surname", app.surname)
    row("First Name", app.first_name)
    row("Other Names", app.other_names)
    row("Telephone", app.telephone)
    row("Email", app.email)
    row("Submitted At", _php_long_datetime(app.submitted_at))

    section_title("Position & Qualifications")
    row("Rank", app.position_rank)
    row("Application Status", app.status or "Pending")
    badge_row("Short Courses", app.short_courses_rmu)
    badge_row("ISPS/GMA", app.familiarisation_isps_gma)
    badge_row("Attachment", app.attachment or "No")
    badge_row("Medicals", app.medicals or "No")

    section_title("Sea Experience")
    badge_row("Has Experience", app.sea_experience or "No")

    # Same year/month split as the PHP version
    years, months = 0, 0
    if app.total_sea_experience_years:
        total = float(app.total_sea_experience_years)
        years = math.floor(total)
        months = round((total - years) * 12)
        if months == 12:
            years += 1
            months = 0
    row("Total Experience", f"{years} Year(s) {months} Month(s)")
    row("Last Ship Type", app.last_ship_type)

    # Footer
    pdf.ln(10)
    pdf.set_font("helvetica", "", 8)
    pdf.set_text_color(*FOOTER_GREY)
    generated_at = _php_long_datetime(datetime.now())
    pdf.cell(0, 5, _latin1(f"Generated on {generated_at} | Application ID: {app.id} | NSPD Ghana"),
             align="C")

    return bytes(pdf.output())
