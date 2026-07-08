"""Real-time job search via the Adzuna API (India only).

Keys are read from the ADZUNA_APP_ID / ADZUNA_APP_KEY environment variables.
If they are missing (or the request fails), ``fetch_live_jobs`` returns an
empty list plus a human-readable reason so the caller can fall back to the
local CSV recommender.
"""

import html
import json
import os
import re
import time
import urllib.parse
import urllib.request

import semantic
from semantic import embed, scale_similarity
from skills_config import extract_skills, is_remote_text

SEMANTIC = semantic.available()

COUNTRY = "in"  # this app searches Indian jobs only
CURRENCY = "₹"
ADZUNA_URL = "https://api.adzuna.com/v1/api/jobs/in/search/{page}?{params}"
_TAG_RE = re.compile(r"<[^>]+>")

# Cities offered in the location dropdown. The value is the ``where`` string
# passed to Adzuna; an empty value means "anywhere in India".
INDIA_CITIES = [
    ("", "All India"),
    ("Bangalore", "Bangalore"),
    ("Hyderabad", "Hyderabad"),
    ("Chennai", "Chennai"),
    ("Mumbai", "Mumbai"),
    ("Pune", "Pune"),
    ("Delhi", "Delhi"),
    ("Gurgaon", "Gurgaon"),
    ("Noida", "Noida"),
    ("Kolkata", "Kolkata"),
    ("Ahmedabad", "Ahmedabad"),
    ("Chandigarh", "Chandigarh"),
    ("Jaipur", "Jaipur"),
    ("Kochi", "Kochi"),
    ("Remote", "Remote"),
]
_VALID_CITIES = {value for value, _ in INDIA_CITIES}

# Simple in-memory response cache (per city/skills) with a short TTL.
_CACHE = {}
_CACHE_TTL = 600  # seconds (10 minutes)


def _clean(text):
    """Strip HTML tags / entities Adzuna sometimes returns in descriptions."""
    return html.unescape(_TAG_RE.sub("", str(text or ""))).strip()


def _semantic_scores(user_skills, job_texts):
    """Cosine similarity of the query against each job text (batched)."""
    if not job_texts:
        return []
    query_vec = embed([f"Skills: {user_skills}"])[0]
    job_vecs = embed(job_texts)  # L2-normalized -> dot == cosine
    return (job_vecs @ query_vec).tolist()


def _format_salary(job):
    lo, hi = job.get("salary_min"), job.get("salary_max")
    if not lo and not hi:
        return ""

    def fmt(v):
        return f"{CURRENCY}{int(round(v)):,}"

    if lo and hi and int(lo) != int(hi):
        text = f"{fmt(lo)}–{fmt(hi)}"
    else:
        text = fmt(lo or hi)
    if str(job.get("salary_is_predicted")) == "1":
        text += " (est.)"
    return text + "/yr"


def fetch_live_jobs(user_skills, where="", limit=50, page=1):
    """Return (results, error). ``error`` is "" on success. India only.

    ``page`` fetches a later page of Adzuna results (each page = one API call);
    used by the on-demand "Show more" pagination.
    """
    app_id = os.getenv("ADZUNA_APP_ID")
    app_key = os.getenv("ADZUNA_APP_KEY")
    if not app_id or not app_key:
        return [], ("Live search needs ADZUNA_APP_ID and ADZUNA_APP_KEY "
                    "environment variables.")

    where = (where or "").strip()
    if where not in _VALID_CITIES:
        where = ""
    page = max(1, int(page))

    user_set = {s.strip().lower() for s in user_skills.split(",") if s.strip()}
    if not user_set:
        return [], ""

    # cache lookup
    cache_key = (where.lower(), tuple(sorted(user_set)), page)
    now_ts = time.time()
    cached = _CACHE.get(cache_key)
    if cached and now_ts - cached[0] < _CACHE_TTL:
        return cached[1], ""

    # Opportunistically drop expired entries so a long-running process doesn't
    # accumulate one cache entry per distinct search forever.
    if len(_CACHE) > 200:
        expired = [k for k, (ts, _) in _CACHE.items() if now_ts - ts >= _CACHE_TTL]
        for k in expired:
            del _CACHE[k]

    query = {
        "app_id": app_id,
        "app_key": app_key,
        "what_or": " ".join(user_set),
        "results_per_page": min(limit, 50),  # Adzuna caps a single page at 50
        "content-type": "application/json",
    }
    if where:
        query["where"] = where
    url = ADZUNA_URL.format(page=page, params=urllib.parse.urlencode(query))

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "job-recommender"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # network / HTTP / JSON errors
        return [], f"Live search is unavailable right now ({type(exc).__name__})."

    jobs = data.get("results", [])

    # Parse each job and build a skill-focused text (used for semantic scoring).
    parsed = []
    job_texts = []
    for job in jobs:
        title = _clean(job.get("title")) or "Job Opening"
        desc = _clean(job.get("description"))
        job_skills = {s.lower() for s in extract_skills(title + " " + desc)}
        parsed.append((job, title, desc, job_skills))
        job_texts.append(f"Skills: {', '.join(sorted(job_skills))}. {title}. {desc[:300]}")

    # Semantic scoring when available; otherwise classic skill-overlap cosine.
    sims = _semantic_scores(user_skills, job_texts) if SEMANTIC else [0.0] * len(parsed)

    results = []
    for (job, title, desc, job_skills), sim in zip(parsed, sims):
        location = _clean((job.get("location") or {}).get("display_name"))
        remote = is_remote_text(title, desc, location)

        matched = job_skills & user_set
        missing = job_skills - user_set
        salary_value = int(job.get("salary_max") or job.get("salary_min") or 0)

        if SEMANTIC:
            # every result is already an India job, so no flat India bonus
            base, india_bonus = scale_similarity(sim), 0.0
        else:
            overlap = (len(user_set) * len(job_skills)) ** 0.5
            base = len(matched) / overlap if overlap else 0.0
            india_bonus = 0.15
        final_score = min(base + india_bonus, 1.0)

        results.append({
            "score": round(final_score * 100, 2),
            "base_score": round(base * 100, 2),
            "india_bonus": round(india_bonus * 100),
            "matched_count": len(matched),
            "required_count": len(job_skills),
            "india_job": True,
            "remote": remote,
            "title": title,
            "company": _clean((job.get("company") or {}).get("display_name")),
            "location": location,
            "salary": _format_salary(job),
            "salary_value": salary_value,
            "link": job.get("redirect_url", ""),
            "skills": ", ".join(sorted(job_skills)),
            "missing_skills": ", ".join(sorted(missing)),
            "summary": desc[:150],
        })

    results.sort(key=lambda x: x["score"], reverse=True)
    _CACHE[cache_key] = (time.time(), results)
    return results, ""
