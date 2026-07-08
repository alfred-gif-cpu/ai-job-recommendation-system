"""Build downloadable CSV / PDF files from the job results a user is viewing.

Takes plain dicts sent from the browser (exactly what's rendered on screen),
so exporting costs no extra Adzuna API calls and always matches what the
user sees.
"""

import csv
import io

from fpdf import FPDF

MAX_JOBS = 200  # sane upper bound on a single export request

FIELDS = ["title", "company", "location", "score", "salary", "skills", "missing", "link"]


def _pdf_safe(text):
    """The core Helvetica font is Latin-1 only (no ₹, emoji, etc.).

    Swap the rupee sign for "Rs." and drop anything else it can't render
    instead of crashing the export.
    """
    text = str(text).replace("₹", "Rs. ")
    return text.encode("latin-1", "ignore").decode("latin-1")


def _clean_rows(jobs):
    rows = []
    for j in (jobs or [])[:MAX_JOBS]:
        if not isinstance(j, dict):
            continue
        rows.append({
            "title": str(j.get("title", ""))[:200],
            "company": str(j.get("company", ""))[:120],
            "location": str(j.get("location", ""))[:120],
            "score": str(j.get("score", ""))[:10],
            "salary": str(j.get("salary", ""))[:60],
            "skills": str(j.get("skills", ""))[:400],
            "missing": str(j.get("missing", ""))[:400],
            "link": str(j.get("link", ""))[:300],
        })
    return rows


def jobs_to_csv(jobs):
    rows = _clean_rows(jobs)
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=FIELDS)
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue().encode("utf-8")


def jobs_to_pdf(jobs):
    rows = [{k: _pdf_safe(v) for k, v in row.items()} for row in _clean_rows(jobs)]
    pdf = FPDF()
    pdf.set_margins(15, 15, 15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Your Job Matches", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=10)
    pdf.set_text_color(90, 90, 90)
    pdf.cell(0, 8, f"{len(rows)} jobs", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    for row in rows:
        pdf.set_text_color(20, 20, 20)
        pdf.set_font("Helvetica", "B", 12)
        title_line = row["title"] or "Job Opening"
        pdf.multi_cell(pdf.epw, 7, title_line)

        pdf.set_font("Helvetica", size=10)
        pdf.set_text_color(70, 70, 70)
        meta = " | ".join(p for p in [row["company"], row["location"], row["salary"]] if p)
        if meta:
            pdf.multi_cell(pdf.epw, 6, meta)
        if row["score"]:
            pdf.multi_cell(pdf.epw, 6, f"Match: {row['score']}%")
        if row["skills"]:
            pdf.multi_cell(pdf.epw, 6, f"Required: {row['skills']}")
        if row["missing"]:
            pdf.multi_cell(pdf.epw, 6, f"To learn: {row['missing']}")
        if row["link"]:
            pdf.set_text_color(37, 99, 235)
            pdf.multi_cell(pdf.epw, 6, row["link"])
        pdf.ln(4)

    return bytes(pdf.output())
