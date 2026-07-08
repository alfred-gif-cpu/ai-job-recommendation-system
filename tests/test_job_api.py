import json
from unittest.mock import MagicMock, patch

import pytest

import job_api


@pytest.fixture(autouse=True)
def clear_cache():
    """job_api caches responses in a module-level dict; isolate tests from it."""
    job_api._CACHE.clear()
    yield
    job_api._CACHE.clear()


def _fake_urlopen(payload):
    """Build a context-manager mock returning the given JSON payload."""
    resp = MagicMock()
    resp.read.return_value = json.dumps(payload).encode("utf-8")
    resp.__enter__.return_value = resp
    resp.__exit__.return_value = False
    return resp


class TestFetchLiveJobsCredentials:
    def test_missing_credentials_returns_helpful_error(self, monkeypatch):
        monkeypatch.delenv("ADZUNA_APP_ID", raising=False)
        monkeypatch.delenv("ADZUNA_APP_KEY", raising=False)
        results, err = job_api.fetch_live_jobs("python, sql")
        assert results == []
        assert "ADZUNA_APP_ID" in err

    def test_empty_skills_returns_no_error(self):
        results, err = job_api.fetch_live_jobs("")
        assert results == []
        assert err == ""


class TestFetchLiveJobsParsing:
    def test_parses_results_and_strips_html(self, sample_adzuna_response):
        with patch("urllib.request.urlopen", return_value=_fake_urlopen(sample_adzuna_response)):
            results, err = job_api.fetch_live_jobs("python, sql, machine learning")
        assert err == ""
        assert len(results) == 3
        # HTML tags/entities from the description must be stripped
        assert "<strong>" not in " ".join(r["summary"] for r in results)
        assert "&amp;" not in " ".join(r["summary"] for r in results)

    def test_scores_are_capped_at_100(self, sample_adzuna_response):
        with patch("urllib.request.urlopen", return_value=_fake_urlopen(sample_adzuna_response)):
            results, _ = job_api.fetch_live_jobs("python, sql, machine learning, aws")
        assert all(r["score"] <= 100 for r in results)

    def test_salary_formatted_with_rupee_and_range(self, sample_adzuna_response):
        with patch("urllib.request.urlopen", return_value=_fake_urlopen(sample_adzuna_response)):
            results, _ = job_api.fetch_live_jobs("python, sql")
        ml_job = next(r for r in results if "Machine Learning" in r["title"])
        assert "₹" in ml_job["salary"]
        assert ml_job["salary_value"] == 1800000

    def test_predicted_salary_is_labeled(self, sample_adzuna_response):
        with patch("urllib.request.urlopen", return_value=_fake_urlopen(sample_adzuna_response)):
            results, _ = job_api.fetch_live_jobs("excel, tableau")
        analyst = next(r for r in results if r["title"] == "Data Analyst")
        assert "(est.)" in analyst["salary"]

    def test_remote_sensing_job_not_flagged_remote(self, sample_adzuna_response):
        # regression: "Remote Sensing Engineer" must not get the Remote badge
        with patch("urllib.request.urlopen", return_value=_fake_urlopen(sample_adzuna_response)):
            results, _ = job_api.fetch_live_jobs("python, sql")
        sensing_job = next(r for r in results if "Sensing" in r["title"])
        assert sensing_job["remote"] is False

    def test_wfh_job_flagged_remote(self, sample_adzuna_response):
        with patch("urllib.request.urlopen", return_value=_fake_urlopen(sample_adzuna_response)):
            results, _ = job_api.fetch_live_jobs("excel, tableau")
        analyst = next(r for r in results if r["title"] == "Data Analyst")
        assert analyst["remote"] is True

    def test_all_results_marked_india_job(self, sample_adzuna_response):
        with patch("urllib.request.urlopen", return_value=_fake_urlopen(sample_adzuna_response)):
            results, _ = job_api.fetch_live_jobs("python, sql")
        assert all(r["india_job"] for r in results)

    def test_network_error_returns_graceful_message(self):
        with patch("urllib.request.urlopen", side_effect=OSError("boom")):
            results, err = job_api.fetch_live_jobs("python, sql")
        assert results == []
        assert "unavailable" in err.lower()

    def test_invalid_city_falls_back_to_all_india(self, sample_adzuna_response):
        with patch("urllib.request.urlopen", return_value=_fake_urlopen(sample_adzuna_response)) as mock_open:
            job_api.fetch_live_jobs("python, sql", where="Not A Real City")
        called_url = mock_open.call_args[0][0].full_url
        assert "where=" not in called_url

    def test_response_is_cached(self, sample_adzuna_response):
        with patch("urllib.request.urlopen", return_value=_fake_urlopen(sample_adzuna_response)) as mock_open:
            job_api.fetch_live_jobs("python, sql", where="Pune")
            job_api.fetch_live_jobs("python, sql", where="Pune")
        assert mock_open.call_count == 1
