from smart_india_recommender import recommend_jobs


class TestRecommendJobs:
    def test_empty_input_returns_no_results(self):
        assert recommend_jobs("") == []
        assert recommend_jobs("   ") == []

    def test_returns_results_for_common_skills(self):
        results = recommend_jobs("python, sql, machine learning")
        assert len(results) > 0

    def test_respects_top_n(self):
        results = recommend_jobs("python, sql, machine learning, aws, java", top_n=5)
        assert len(results) <= 5

    def test_score_never_exceeds_100(self):
        results = recommend_jobs("python, sql, machine learning, aws")
        assert all(r["score"] <= 100 for r in results)

    def test_results_sorted_by_score_descending(self):
        results = recommend_jobs("python, sql, machine learning, aws, docker")
        scores = [r["score"] for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_result_shape_has_expected_fields(self):
        results = recommend_jobs("python, sql")
        assert results, "expected at least one result to check shape"
        job = results[0]
        for field in (
            "score", "base_score", "india_bonus", "matched_count",
            "required_count", "india_job", "remote", "title", "company",
            "link", "skills", "missing_skills", "summary",
        ):
            assert field in job

    def test_matched_and_missing_skills_are_consistent(self):
        results = recommend_jobs("python, sql")
        for job in results:
            job_skills = {s.strip() for s in job["skills"].split(",") if s.strip()}
            missing = {s.strip() for s in job["missing_skills"].split(",") if s.strip()}
            # missing skills must be a subset of the job's required skills
            assert missing <= job_skills
            assert job["matched_count"] + len(missing) == job["required_count"]
