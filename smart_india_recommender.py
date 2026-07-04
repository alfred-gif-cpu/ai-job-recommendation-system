import re
from urllib.parse import unquote, urlparse

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# ===============================
# LOAD DATASET
# ===============================
df = pd.read_csv("jobs_with_skills.csv")

# remove empty skills and reset index so positional lookups stay aligned
df = df.dropna(subset=["skills"]).reset_index(drop=True)

# ===============================
# INDIA KEYWORDS
# ===============================
india_keywords = [
    "india",
    "bangalore",
    "bengaluru",
    "hyderabad",
    "chennai",
    "mumbai",
    "pune",
    "delhi",
    "gurgaon",
    "noida",
    "remote india",
]

# Precompute the India flag once per job instead of scanning the summary
# text on every single request.
_summary_lower = df["job_summary"].astype(str).str.lower()
_india_pattern = "|".join(re.escape(k) for k in india_keywords)
df["is_india"] = _summary_lower.str.contains(_india_pattern, na=False)

# ===============================
# VECTORIZE SKILLS
# ===============================
vectorizer = CountVectorizer()
job_vectors = vectorizer.fit_transform(df["skills"])


# ===============================
# JOB TITLE / COMPANY FROM LINK
# ===============================
def parse_job_link(link):
    """Extract a readable title + company from a LinkedIn-style job URL.

    Links look like:
    https://.../jobs/view/store-manager-at-goodwill-industries-3766724818
    -> title="Store Manager", company="Goodwill Industries"
    """
    title, company = "Job Opening", ""
    try:
        path = unquote(urlparse(str(link)).path).rstrip("/")
        slug = path.split("/view/")[-1] if "/view/" in path else path.split("/")[-1]
        slug = re.sub(r"-\d+$", "", slug)  # drop the trailing numeric job id
        if "-at-" in slug:
            title_part, company_part = slug.split("-at-", 1)
        else:
            title_part, company_part = slug, ""
        title = title_part.replace("-", " ").strip().title() or "Job Opening"
        company = company_part.replace("-", " ").strip().title()
    except Exception:
        pass
    return title, company


# ===============================
# MAIN FUNCTION (USED BY FLASK)
# ===============================
def recommend_jobs(user_skills, top_n=12):
    user_skills = str(user_skills).lower().strip()
    user_set = {s.strip() for s in user_skills.split(",") if s.strip()}

    if not user_set:
        return []

    user_vector = vectorizer.transform([user_skills])
    scores = cosine_similarity(user_vector, job_vectors)[0]

    if not scores.any():
        return []

    # Only re-rank a bounded pool of the strongest cosine matches instead of
    # looping over every row (~53k). The India bonus can only reshuffle within
    # this pool, which keeps requests fast without changing the top results.
    pool_size = min(len(scores), max(top_n * 20, 100))
    candidate_idx = np.argpartition(scores, -pool_size)[-pool_size:]

    results = []
    for i in candidate_idx:
        score = float(scores[i])
        if score <= 0:
            continue

        row = df.iloc[i]
        summary_text = str(row["job_summary"]).lower()
        india_bonus = 0.15 if row["is_india"] else 0.0
        remote = "remote" in summary_text or "work from home" in summary_text

        # Cap at 1.0 so the score / progress bar never exceeds 100%.
        final_score = min(score + india_bonus, 1.0)

        job_skills = {s.strip() for s in str(row["skills"]).split(",") if s.strip()}
        matched = job_skills & user_set
        missing = job_skills - user_set

        title, company = parse_job_link(row["job_link"])

        results.append({
            "score": round(final_score * 100, 2),
            # breakdown used by the ring tooltip
            "base_score": round(score * 100, 2),
            "india_bonus": round(india_bonus * 100),
            "matched_count": len(matched),
            "required_count": len(job_skills),
            "india_job": india_bonus > 0,
            "remote": remote,
            "title": title,
            "company": company,
            "link": row["job_link"],
            "skills": row["skills"],
            "missing_skills": ", ".join(sorted(missing)),
            "summary": str(row["job_summary"])[:150],
        })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_n]
