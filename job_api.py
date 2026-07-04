"""Real-time job search via the Adzuna API (India only).

Keys are read from the ADZUNA_APP_ID / ADZUNA_APP_KEY environment variables.
If they are missing (or the request fails), ``fetch_live_jobs`` returns an
empty list plus a human-readable reason so the caller can fall back to the
local CSV recommender.
"""

import html
import json
import math
import os
import re
import time
import urllib.parse
import urllib.request

from skills_config import extract_skills

COUNTRY = "in"  # this app searches Indian jobs only
CURRENCY = "₹"
ADZUNA_URL = "https://api.adzuna.com/v1/api/jobs/in/search/1?{params}"
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


def fetch_live_jobs(user_skills, where="", limit=24):
    """Return (results, error). ``error`` is "" on success. India only."""
    app_id = os.getenv("ADZUNA_APP_ID")
    app_key = os.getenv("ADZUNA_APP_KEY")
    if not app_id or not app_key:
        return [], ("Live search needs ADZUNA_APP_ID and ADZUNA_APP_KEY "
                    "environment variables.")

    where = (where or "").strip()
    if where not in _VALID_CITIES:
        where = ""

    user_set = {s.strip().lower() for s in user_skills.split(",") if s.strip()}
    if not user_set:
        return [], ""

    # cache lookup
    cache_key = (where.lower(), tuple(sorted(user_set)))
    cached = _CACHE.get(cache_key)
    if cached and time.time() - cached[0] < _CACHE_TTL:
        return cached[1], ""

    query = {
        "app_id": app_id,
        "app_key": app_key,
        "what_or": " ".join(user_set),
        "results_per_page": limit,
        "content-type": "application/json",
    }
    if where:
        query["where"] = where
    url = ADZUNA_URL.format(params=urllib.parse.urlencode(query))

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "job-recommender"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # network / HTTP / JSON errors
        return [], f"Live search is unavailable right now ({type(exc).__name__})."

    india_bonus = 0.15
    results = []

    for job in data.get("results", []):
        title = _clean(job.get("title")) or "Job Opening"
        desc = _clean(job.get("description"))
        location = _clean((job.get("location") or {}).get("display_name"))
        remote = "remote" in (title + " " + desc + " " + location).lower() \
            or "work from home" in (desc + " " + location).lower()

        job_skills = {s.lower() for s in extract_skills(title + " " + desc)}
        matched = job_skills & user_set
        missing = job_skills - user_set
        salary_value = int(job.get("salary_max") or job.get("salary_min") or 0)

        # cosine similarity on binary skill-presence vectors
        if user_set and job_skills:
            sim = len(matched) / math.sqrt(len(user_set) * len(job_skills))
        else:
            sim = 0.0
        final_score = min(sim + india_bonus, 1.0)

        results.append({
            "score": round(final_score * 100, 2),
            "base_score": round(sim * 100, 2),
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
            "skills": ", ".join(sorted(job_skills)) if job_skills else "—",
            "missing_skills": ", ".join(sorted(missing)),
            "summary": desc[:150],
        })

    results.sort(key=lambda x: x["score"], reverse=True)
    _CACHE[cache_key] = (time.time(), results)
    return results, ""
