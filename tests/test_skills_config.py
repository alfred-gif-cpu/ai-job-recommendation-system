from skills_config import extract_skills, is_remote_text, learn_link


class TestExtractSkills:
    def test_detects_master_list_skills(self):
        text = "Experienced in Python, SQL, Machine Learning and AWS."
        found = extract_skills(text)
        assert set(found) == {"python", "sql", "machine learning", "aws"}

    def test_cplusplus_is_detected(self):
        # regression: \bc\+\+\b can never match (no word boundary after '+')
        assert extract_skills("c++ developer") == ["c++"]
        assert extract_skills("expert in c++") == ["c++"]
        assert extract_skills("C++ and Python") == ["python", "c++"]

    def test_aliases_resolve_to_canonical_skill(self):
        text = "ML and DL with JS, TS, k8s, postgres, mongo, sklearn, cpp"
        found = set(extract_skills(text))
        assert found == {
            "machine learning", "deep learning", "javascript", "typescript",
            "kubernetes", "postgresql", "mongodb", "scikit-learn", "c++",
        }

    def test_no_false_positive_on_substrings(self):
        assert extract_skills("chemical reaction engineer") == []
        assert extract_skills("html5 markup") == []
        assert extract_skills("a 5ml sample") == []

    def test_empty_and_non_string_input(self):
        assert extract_skills("") == []
        assert extract_skills(None) == []

    def test_results_are_deduplicated_and_ordered(self):
        found = extract_skills("python python PYTHON sql")
        assert found.count("python") == 1
        # order follows the master list, not the text
        assert found == ["python", "sql"]


class TestIsRemoteText:
    def test_remote_sensing_is_not_flagged_remote(self):
        assert is_remote_text(
            "Remote Sensing Engineer",
            "satellite remote sensing and GIS analysis, in-office role",
            "Bangalore",
        ) is False

    def test_genuine_remote_jobs_are_flagged(self):
        assert is_remote_text("Software Engineer", "fully remote position") is True
        assert is_remote_text("Analyst", "this is a WFH role") is True
        assert is_remote_text("Developer", "you can work remotely 3 days a week") is True

    def test_mixed_remote_sensing_and_remote_work(self):
        # stripping "remote sensing" shouldn't blind it to a genuine remote
        # mention elsewhere in the same text
        assert is_remote_text(
            "GIS + Remote hybrid",
            "remote sensing analyst, fully remote position available",
        ) is True

    def test_non_remote_office_job(self):
        assert is_remote_text("Office Manager", "in-office administrative role", "Delhi") is False


class TestLearnLink:
    def test_generates_youtube_search_url(self):
        url = learn_link("python")
        assert url.startswith("https://www.youtube.com/results?search_query=")
        assert "python" in url

    def test_url_encodes_special_characters(self):
        assert "%2B%2B" in learn_link("c++")
        assert "%2F" in learn_link("ui/ux design")
