import os
import re
from urllib.parse import unquote, urlparse

import numpy as np
import pandas as pd

import semantic

# ===============================
# LOAD DATASET (must match build_embeddings.py ordering)
# ===============================
df = pd.read_csv("jobs_with_skills.csv").dropna(subset=["skills"]).reset_index(drop=True)

# ===============================
# INDIA / REMOTE FLAGS
# ===============================
india_keywords = [
    "india", "bangalore", "bengaluru", "hyderabad", "chennai", "mumbai",
    "pune", "delhi", "gurgaon", "noida", "remote india",
]
_summary_lower = df["job_summary"].astype(str).str.lower()
_india_pattern = "|".join(re.escape(k) for k in india_keywords)
df["is_india"] = _summary_lower.str.contains(_india_pattern, na=False)
df["is_remote"] = _summary_lower.str.contains("remote|work from home", na=False)

# ===============================
# MATCHING BACKEND
# Semantic (embeddings) when enabled + available, else classic bag-of-words.
# ===============================
SEMANTIC = semantic.available() and os.path.exists("job_embeddings.npy")

if SEMANTIC:
    job_embeddings = np.load("job_embeddings.npy")
else:
    from sklearn.feature_extraction.text import CountVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    _vectorizer = CountVectorizer()
    _job_vectors = _vectorizer.fit_transform(df["skills"])


# ===============================
# JOB TITLE / COMPANY FROM LINK
# ===============================
def parse_job_link(link):
    """Extract a readable title + company from a LinkedIn-style job URL."""
    title, company = "Job Opening", ""
    try:
        path = unquote(urlparse(str(link)).path).rstrip("/")
        slug = path.split("/view/")[-1] if "/view/" in path else path.split("/")[-1]
        slug = re.sub(r"-\d+$", "", slug)
        if "-at-" in slug:
            title_part, company_part = slug.split("-at-", 1)
        else:
            title_part, company_part = slug, ""
        title = title_part.replace("-", " ").strip().title() or "Job Opening"
        company = company_part.replace("-", " ").strip().title()
    except Exception:
        pass
    return title, company


def _build_result(row, base, india_bonus, user_set):
    final_score = min(base + india_bonus, 1.0)
    job_skills = {s.strip() for s in str(row["skills"]).split(",") if s.strip()}
    matched = job_skills & user_set
    missing = job_skills - user_set
    title, company = parse_job_link(row["job_link"])
    return {
        "score": round(final_score * 100, 2),
        "base_score": round(base * 100, 2),
        "india_bonus": round(india_bonus * 100),
        "matched_count": len(matched),
        "required_count": len(job_skills),
        "india_job": bool(row["is_india"]),
        "remote": bool(row["is_remote"]),
        "title": title,
        "company": company,
        "link": row["job_link"],
        "skills": row["skills"],
        "missing_skills": ", ".join(sorted(missing)),
        "summary": str(row["job_summary"])[:150],
    }


# ===============================
# MAIN FUNCTION (USED BY FLASK)
# ===============================
def recommend_jobs(user_skills, top_n=50):
    user_skills = str(user_skills).lower().strip()
    user_set = {s.strip() for s in user_skills.split(",") if s.strip()}
    if not user_set:
        return []

    if SEMANTIC:
        # embed query in the same "Skills: ..." framing as the docs
        query_vec = semantic.embed([f"Skills: {user_skills}"])[0]
        scores = job_embeddings @ query_vec  # L2-normalized -> cosine
        base_of = lambda i: semantic.scale_similarity(scores[i])
    else:
        user_vector = _vectorizer.transform([user_skills])
        scores = cosine_similarity(user_vector, _job_vectors)[0]
        base_of = lambda i: float(scores[i])

    pool = min(len(scores), max(top_n * 4, 200))
    candidate_idx = np.argpartition(scores, -pool)[-pool:]

    results = []
    for i in candidate_idx:
        base = base_of(i)
        if base <= 0:
            continue
        row = df.iloc[i]
        india_bonus = 0.15 if row["is_india"] else 0.0
        results.append(_build_result(row, base, india_bonus, user_set))

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_n]
