import io

from app import dedupe_skills


class TestDedupeSkills:
    def test_removes_duplicates_case_insensitively(self):
        assert dedupe_skills("Python, python, PYTHON, sql") == ["Python", "sql"]

    def test_strips_whitespace_and_empties(self):
        assert dedupe_skills(" python ,  , sql ,") == ["python", "sql"]


class TestHomeRoute:
    def test_get_with_no_params_shows_blank_state(self, client):
        r = client.get("/")
        assert r.status_code == 200
        assert b"Recommended Jobs" not in r.data

    def test_get_with_skills_param_returns_results(self, client):
        r = client.get("/?skills=" + "python,sql,machine%20learning")
        assert r.status_code == 200
        assert b"card" in r.data

    def test_empty_post_shows_prompt_message(self, client):
        r = client.post("/", data={})
        assert r.status_code == 200
        assert b"Please enter your skills or upload a resume" in r.data

    def test_manual_skills_post_returns_results(self, client):
        r = client.post("/", data={"skills": "python, sql, machine learning"})
        assert r.status_code == 200
        assert b"card" in r.data

    def test_resume_upload_prefills_skills_box(self, client, pdf_resume_bytes):
        data = {"resume": (io.BytesIO(pdf_resume_bytes), "resume.pdf")}
        r = client.post("/", data=data, content_type="multipart/form-data")
        assert r.status_code == 200
        assert b"Please upload a PDF" not in r.data
        assert b"card" in r.data

    def test_docx_resume_upload_works(self, client, docx_resume_bytes):
        data = {"resume": (io.BytesIO(docx_resume_bytes), "resume.docx")}
        r = client.post("/", data=data, content_type="multipart/form-data")
        assert r.status_code == 200
        assert b"card" in r.data

    def test_unsupported_file_type_rejected(self, client):
        data = {"resume": (io.BytesIO(b"hello"), "resume.txt")}
        r = client.post("/", data=data, content_type="multipart/form-data")
        assert r.status_code == 200
        assert b"PDF or Word" in r.data

    def test_changing_city_after_resume_upload_does_not_require_reupload(self, client, pdf_resume_bytes):
        # first: upload resume
        data = {"resume": (io.BytesIO(pdf_resume_bytes), "resume.pdf")}
        r1 = client.post("/", data=data, content_type="multipart/form-data")
        text = r1.get_data(as_text=True)
        import re
        m = re.search(r'id="skills"[^>]*value="([^"]*)"', text)
        assert m, "expected the detected skills to be pre-filled in the skills box"
        skills = m.group(1)

        # then: resubmit with just the carried-over skills + a new city, no file
        r2 = client.post("/", data={"skills": skills, "where": "Pune"})
        assert r2.status_code == 200
        assert b"Please upload a PDF" not in r2.data
        assert b"card" in r2.data


class TestLiveMoreRoute:
    def test_no_skills_returns_empty_result(self, client):
        r = client.get("/live-more?skills=&page=2")
        assert r.status_code == 200
        assert r.get_json()["count"] == 0

    def test_page_below_2_returns_empty_result(self, client):
        r = client.get("/live-more?skills=python,sql&page=1")
        assert r.get_json()["count"] == 0


class TestExportRoute:
    def test_export_csv(self, client):
        jobs = [{"title": "ML Engineer", "company": "Acme", "score": "90", "link": "https://x.com"}]
        r = client.post("/export", json={"format": "csv", "jobs": jobs})
        assert r.status_code == 200
        assert r.content_type.startswith("text/csv")

    def test_export_pdf(self, client):
        jobs = [{"title": "ML Engineer", "company": "Acme", "score": "90", "link": "https://x.com"}]
        r = client.post("/export", json={"format": "pdf", "jobs": jobs})
        assert r.status_code == 200
        assert r.content_type == "application/pdf"

    def test_export_with_no_jobs_returns_400(self, client):
        r = client.post("/export", json={"format": "csv", "jobs": []})
        assert r.status_code == 400
