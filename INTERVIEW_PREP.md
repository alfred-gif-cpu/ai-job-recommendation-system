# Interview Prep: Job Recommendation System

This is your prep sheet for talking through this project in a software
engineering interview. It's organized as: a pitch you can give in 30 seconds,
the architecture in more depth, the decisions worth defending, likely
questions with answers grounded in the actual code, and the honest weak spots
you should be ready to admit rather than get caught out on.

---

## 1. The 30-second pitch

> "It's a Flask web app that matches a user's skills — typed in or pulled from
> an uploaded resume — against job listings, using cosine similarity over
> skill vectors, and ranks the results. It can run against a bundled offline
> dataset or pull real-time listings from the Adzuna API. The interesting
> engineering bits are: it degrades gracefully when the external API is
> unavailable, it has a feature flag that swaps the matching algorithm based
> on the host's memory budget, and it's got a pytest suite covering the
> matching logic, the API integration (via mocked requests), and the Flask
> routes."

If they want the one-line version: **"A resume-to-job matcher with a live job
API integration, built with attention to failure modes and resource
constraints, not just the happy path."**

---

## 2. Architecture, in more depth

```
Browser (Jinja2-rendered HTML + vanilla JS)
   │
   ├── POST/GET /            → app.py: home()
   │      ├── resume upload  → extract_text_from_pdf/docx → skills_config.extract_skills()
   │      ├── manual skills  → skills_config.dedupe_skills()
   │      └── find_jobs(skills, live, where, ip)
   │              ├── live=True  → job_api.fetch_live_jobs()  → Adzuna API (rate-limited, cached)
   │              └── live=False → smart_india_recommender.recommend_jobs() → local CSV
   │
   ├── GET  /live-more       → on-demand pagination (fetch next Adzuna page)
   └── POST /export          → export_utils.jobs_to_csv/pdf (built from what's already on screen)
```

**Matching backend (the part worth walking through carefully):**

- Default: `CountVectorizer` (scikit-learn) turns each job's skill list into a
  bag-of-words vector; the user's skills are vectorized the same way; cosine
  similarity ranks jobs against the query.
- Optional: `sentence-transformers` embeddings (`all-MiniLM-L6-v2`) for
  semantic similarity — understands that "ML" and "machine learning" are
  related by meaning, not just by an alias table.
- Both live behind the same interface (`recommend_jobs()` / `fetch_live_jobs()`
  return the same shaped dict), so the caller doesn't know or care which one
  is active. The switch is `smart_india_recommender.SEMANTIC` /
  `job_api.SEMANTIC`, set once at import time from the `USE_SEMANTIC` env var.

**Why two backends instead of just using the better one everywhere:** the
embeddings model needs PyTorch, which needs roughly 1–2 GB of RAM to load.
The app is deployed on Render's free tier, which caps at 512 MB. Loading
PyTorch there would either fail the build or get the process OOM-killed at
runtime. So the flag lets me keep one codebase that's lean in production and
richer wherever there's more memory to spare — rather than maintaining two
separate matching implementations, or gambling on the free tier and taking
the live site down.

---

## 3. Decisions worth being able to defend

**Q: "Why Flask, not FastAPI or Django?"**
Flask fits the scope: mostly server-rendered pages, a couple of JSON
endpoints, no need for an ORM or admin panel (Django) or async I/O at
this scale (FastAPI's main edge). If this needed to handle a lot of
concurrent long-lived connections or heavy async fan-out to multiple
external APIs, I'd reconsider FastAPI.

**Q: "Why in-memory rate limiting and caching instead of Redis?"**
Because the app runs as a single process on a single free-tier instance —
Redis would be infrastructure for a scaling problem I don't have yet. The
limiter (`rate_limit.py`) and the live-search cache (`job_api._CACHE`) are
both plain dicts protected by a lock, with periodic pruning so they don't
grow unbounded (that was actually a real bug I found and fixed during a
self-review — see section 5). If this needed multiple worker processes or
horizontal scaling, in-memory state stops working (each process would have
its own cache/limiter) and I'd move to Redis at that point — but not before,
since it'd be unjustified complexity for the current deployment.

**Q: "Why does resume parsing use keyword matching instead of an NLP
model?"**
Two reasons. First, deliberately no external API calls in the resume-parsing
path — running a hosted LLM call on every resume upload adds latency, cost,
and a hard dependency for something that a curated list handles well enough:
skills on a resume are mostly named literally ("Python", "React", "AWS").
Second, when I did want smarter matching, I added it as an opt-in local
embeddings model rather than reaching for an API — same reasoning, just
applied to the *matching* step instead of the *extraction* step.

**Q: "Walk me through what happens if Adzuna is down or misconfigured."**
`fetch_live_jobs()` catches the request exception and returns an empty list
plus an error string instead of raising. `find_jobs()` in `app.py` sees that
error, falls back to `recommend_jobs()` (the offline dataset), and passes the
error through as a user-facing message ("Live search is unavailable right
now... showing sample matches instead."). The user never sees a stack trace
or a blank page — worst case, they get sample data with an explanation of
why.

**Q: "How do you protect the Adzuna API quota?"**
Two layers: a 10-minute in-memory cache keyed on (city, skills, page), so
repeat searches don't re-hit the API, and a sliding-window rate limiter
(20 requests/minute per IP, shared between the main search and the
pagination endpoint) so a runaway client or accidental loop can't drain the
free-tier quota. When the limiter trips, it falls back to the offline
dataset with an explanatory message — same graceful-degradation pattern as
the API-down case.

---

## 4. Questions they'll probably ask, and how to answer

**"Tell me about a bug you found and how you found it."**
Good one to have ready — pick something concrete, not "I fixed a typo":
> "I did a deliberate audit pass over the whole codebase and found that jobs
> titled things like 'Remote Sensing Engineer' — a real, unrelated
> engineering discipline involving satellite imagery — were being flagged as
> work-from-home jobs, because the remote-detection logic was a naive
> substring check for 'remote'. I fixed it by stripping out 'remote sensing'
> phrases before checking, and wrote both a positive test (genuine remote
> jobs still match, including trickier forms like 'you can work remotely')
> and a regression test for the original false positive, so it can't
> silently come back."

**"How do you test something that depends on a third-party API?"**
> "I don't hit the real API in tests — I mock `urllib.request.urlopen` with a
> realistic Adzuna JSON payload and assert on the parsing/scoring logic:
> HTML stripping, salary formatting, the remote-sensing false positive,
> caching behavior (second identical call shouldn't re-hit the mock). The
> live integration itself I verified manually against the real API during
> development."

**"What would break first if this got real traffic?"**
> "The in-memory rate limiter and cache — they're per-process, so with
> multiple gunicorn workers each would have its own view of 'how many
> requests has this IP made,' making the limit effectively N times looser
> than intended. That's the first thing I'd move to Redis if this needed to
> scale horizontally."

**"How would you add user accounts / saved jobs?"**
> "The app is currently fully stateless — no database, no sessions beyond
> what's in the browser's localStorage (recent searches, theme, last city).
> I'd add a database (Postgres, probably, given Render supports it easily),
> a users table, and a saved-jobs join table, plus actual auth. It's a
> meaningfully bigger change than anything currently in the app, which is
> why it's in 'Future Improvements' rather than half-built."

**"Why cosine similarity and not something like TF-IDF or a trained
classifier?"**
> "Cosine similarity over CountVectorizer vectors is simple, fast, and good
> enough for short skill lists — most of the signal is just 'do the same
> skill tokens appear.' TF-IDF would help distinguish common vs. rare skills
> if the skill vocabulary were much larger and I had frequency data to learn
> from. A trained classifier would need labeled ground truth of what a 'good
> match' actually is, which I don't have — this is unsupervised similarity,
> not a trained model, and I'd say that plainly if asked whether it's
> 'AI-powered' — it's classical NLP/IR technique, not a trained model."

**"What's the most interesting tradeoff you made?"**
The semantic-matching flag (section 2/3) is the strongest answer — it shows
you reasoned about a real constraint (deploy host memory) rather than just
picking "the best model" by default.

---

## 5. Be upfront about these — don't get caught flat-footed

Interviewers respect "here's what I'd change" more than a pitch with no
seams. Know these cold:

- **No database, fully stateless.** Everything server-side is recomputed per
  request; the only persistence is client-side localStorage. Fine for this
  scope, a real limitation for anything needing accounts or history across
  devices.
- **In-memory rate limiting/caching doesn't survive a restart or scale across
  processes.** Acceptable for a single free-tier instance; a real constraint
  if this needed to scale out.
- **Skill extraction is keyword/alias matching, not NLP.** It'll miss any
  skill phrased in a way that isn't in the list (~92 entries + aliases). I
  found and fixed a couple of extraction bugs during a self-review (the
  `c++` word-boundary issue, some missing aliases) — a good sign is knowing
  the failure mode, not claiming it's flawless.
- **Automated tests cover the default matching backend, not the optional
  semantic one.** The semantic backend needs a downloaded model file, so it's
  verified manually rather than in CI. Worth saying plainly rather than
  implying full coverage.
- **The offline dataset is small and generic** (~1,200 rows scraped once) —
  it's a fallback, not the main product; the real value is in the live
  Adzuna integration.

---

## 6. Quick glossary (in case of a follow-up you didn't expect)

- **Cosine similarity:** measures the angle between two vectors, ignoring
  magnitude — used here to compare "vector of skills the user has" against
  "vector of skills a job wants."
- **Bag-of-words / CountVectorizer:** turns text into a vector counting which
  words appear, with no notion of word meaning or order.
- **Embeddings:** a model-produced vector representation of text that
  captures meaning, so semantically similar phrases end up as nearby
  vectors even without shared words.
- **Rate limiting (sliding window):** track timestamps of recent calls per
  key; reject if more than N fall within the last window (here: dict of
  deques, 20 calls / 60s per IP).
- **Graceful degradation:** when a dependency fails, fall back to reduced
  functionality instead of failing the whole request.
- **Feature flag:** a runtime switch (here, an env var) that changes
  behavior without a code change or redeploy branch.
