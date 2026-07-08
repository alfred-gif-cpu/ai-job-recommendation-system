from export_utils import jobs_to_csv, jobs_to_pdf

SAMPLE_JOBS = [
    {
        "title": "Machine Learning Engineer",
        "company": "CES Info",
        "location": "Hyderabad",
        "score": "92",
        "salary": "₹15,00,000/yr",
        "skills": "python, sql, machine learning",
        "missing": "aws",
        "link": "https://adzuna.in/details/1",
    },
    {
        "title": "Data Scientist",
        "company": "Acme",
        "location": "Pune",
        "score": "88",
        "salary": "",
        "skills": "python, pandas",
        "missing": "sql, aws",
        "link": "https://adzuna.in/details/2",
    },
]


class TestJobsToCsv:
    def test_produces_header_and_rows(self):
        csv_bytes = jobs_to_csv(SAMPLE_JOBS)
        text = csv_bytes.decode("utf-8")
        lines = text.strip().splitlines()
        assert lines[0].startswith("title,company,location,score,salary,skills,missing,link")
        assert len(lines) == 3  # header + 2 jobs

    def test_preserves_rupee_symbol(self):
        text = jobs_to_csv(SAMPLE_JOBS).decode("utf-8")
        assert "₹" in text

    def test_empty_list_does_not_crash(self):
        text = jobs_to_csv([]).decode("utf-8")
        assert "title" in text  # header only

    def test_non_dict_entries_are_skipped(self):
        csv_bytes = jobs_to_csv(SAMPLE_JOBS + ["not a dict", 42, None])
        lines = csv_bytes.decode("utf-8").strip().splitlines()
        assert len(lines) == 3  # header + the 2 real jobs, junk ignored

    def test_truncates_to_max_jobs(self):
        many_jobs = SAMPLE_JOBS * 150  # 300 jobs, over MAX_JOBS=200
        lines = jobs_to_csv(many_jobs).decode("utf-8").strip().splitlines()
        assert len(lines) - 1 == 200


class TestJobsToPdf:
    def test_produces_valid_pdf_bytes(self):
        pdf_bytes = jobs_to_pdf(SAMPLE_JOBS)
        assert pdf_bytes[:4] == b"%PDF"

    def test_rupee_symbol_does_not_crash_pdf_generation(self):
        # regression: fpdf2's core Helvetica font is Latin-1 only
        pdf_bytes = jobs_to_pdf(SAMPLE_JOBS)
        assert len(pdf_bytes) > 0

    def test_empty_list_does_not_crash(self):
        pdf_bytes = jobs_to_pdf([])
        assert pdf_bytes[:4] == b"%PDF"

    def test_long_unbroken_string_does_not_crash(self):
        jobs = [{**SAMPLE_JOBS[0], "title": "a" * 500}]
        pdf_bytes = jobs_to_pdf(jobs)
        assert pdf_bytes[:4] == b"%PDF"
