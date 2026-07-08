# 🚀 Job Recommendation System

A full-stack Flask web application that matches user skills (typed in, or
extracted from an uploaded resume) against job listings — either a bundled
offline dataset or real-time results from the Adzuna API — and ranks them by
relevance.

Beyond the core matching, the project is built around a few concrete
software-engineering concerns: graceful degradation when an external API is
unavailable, a feature flag that swaps the matching backend based on host
memory constraints, in-memory caching and rate limiting to protect a
third-party API quota, and a pytest suite covering the matching logic, the
live API integration, and the Flask routes.

## ✨ Features

- 📄 Resume upload (PDF or Word .docx) and skill extraction
- 🧠 Skill detection across 92 skills, including common aliases ("ML", "k8s", "c++")
- 🤖 Job matching via cosine similarity (bag-of-words by default; optional local sentence-embedding backend for semantic matching)
- 🔴 Real-time job search via the Adzuna API, with automatic fallback to a bundled offline dataset if the API is unavailable or unconfigured
- 🔗 Real job titles, companies & one-click "Apply / View Job" links
- 🎯 "Skills to Learn" gap analysis, each linked to a tutorial search, + matched/required skill meter per job
- 🔍 Match-breakdown tooltip on each score ring
- 🇮🇳 India-focused live search (city selector) with an India-preference ranking bonus for the offline dataset
- 🌗 Dark / light theme toggle, sort & filter, on-demand pagination
- 🔗 Shareable results links + recent-search history
- 📈 "Top skills in these results" insights panel
- ⬇️ Export your matches as CSV or PDF
- 🛡️ Rate-limited live search to protect the Adzuna free quota
- 🛡️ Graceful handling of empty input, non-PDF/scanned files & no-match cases

## 🛠 Tech Stack

- **Backend:** Python, Flask, gunicorn
- **Matching:** scikit-learn (CountVectorizer + cosine similarity); optional sentence-transformers embeddings
- **Data:** Pandas, NumPy
- **Resume parsing:** PyPDF2, python-docx
- **Export:** fpdf2 (PDF), stdlib csv
- **Testing:** pytest (58 tests covering matching, the Adzuna integration via mocked requests, rate limiting, exports, and Flask routes)
- **Frontend:** server-rendered Jinja2 templates, vanilla JS (no framework), hand-written CSS
- **Deployment:** Render (see below)

## 📌 How it Works

1. User enters skills or uploads a resume (PDF/DOCX)
2. Skills are extracted via a curated keyword/alias matcher
3. Job listings (offline CSV or live Adzuna results) are vectorized and scored against the user's skills via cosine similarity
4. Results are ranked, with an India-preference bonus applied to the offline dataset
5. Results are shown with a match percentage, matched vs. missing skills, and (for live results) salary and location

## 🏗 Architecture notes

A few design decisions worth calling out, since they came from real constraints rather than defaults:

- **Two matching backends behind one interface.** The default matcher is a classic bag-of-words model (scikit-learn). A second backend using local sentence-transformer embeddings is available for semantic matching (e.g. "ML" ≈ "machine learning" by meaning, not just alias lookup), gated by a `USE_SEMANTIC` environment flag. It's off by default because the embedding model needs PyTorch (~1–2 GB RAM), which doesn't fit the free-tier host this app is deployed on. The flag lets the same codebase run lean in production and richer in a bigger environment, without maintaining two codebases.
- **Graceful degradation over hard failures.** If the Adzuna API key is missing, the request fails, or the rate limit is hit, the app falls back to the offline dataset and tells the user why, rather than showing an error page.
- **Rate limiting + caching on the live search path.** A simple in-memory sliding-window limiter and a short-TTL response cache protect the (free-tier) Adzuna API quota from being drained by repeat or runaway requests.
- **Export re-uses rendered data instead of re-querying.** CSV/PDF export is built from what's already rendered in the browser, so it costs zero additional API calls.

## ▶️ Run Locally

```bash
pip install -r requirements.txt
python app.py
# open http://localhost:10000
```

## ✅ Running the tests

```bash
pip install -r requirements.txt -r requirements-dev.txt
pytest
```

The suite runs against the default (classic) matching backend — fast and
deterministic, no model download required. The semantic backend is covered
by manual verification (see the section below) rather than the automated
suite, since it requires downloading a model file.

## 🔴 Real-time jobs (Adzuna)

Flip the **Live jobs** toggle to search real, current openings across India via
the free [Adzuna API](https://developer.adzuna.com/). Pick a **city**
(Bangalore, Hyderabad, Mumbai, Pune, Delhi, Remote, … or All India), and each
result shows its **salary range** in ₹ where available. Results can be filtered
(Remote / With-salary) and sorted by salary, and your last city + filter are
remembered. Responses are cached in-memory for 10 minutes to keep repeat
searches fast, and a rate limit protects the free API quota.

### Adding your Adzuna API key

1. Create a free account at **https://developer.adzuna.com/** and copy your
   **Application ID** and **Application Key**.
2. Add them one of two ways:

   **Option A — `.env` file (easiest):** copy `.env.example` to `.env` and fill
   in your keys. It is git-ignored, so your keys stay private:
   ```
   ADZUNA_APP_ID=your_app_id
   ADZUNA_APP_KEY=your_app_key
   ```

   **Option B — environment variables:**
   ```bash
   # Windows PowerShell
   $env:ADZUNA_APP_ID="your_app_id"; $env:ADZUNA_APP_KEY="your_app_key"; python app.py

   # macOS / Linux
   ADZUNA_APP_ID=your_app_id ADZUNA_APP_KEY=your_app_key python app.py
   ```
3. Start the app and flip the **Live jobs** toggle.

Without keys, live search safely falls back to the bundled sample dataset and
tells you why. No extra dependencies are needed — the client uses the standard
library.

## 🧠 Semantic matching backend (optional, local)

By default the app matches skills with a fast classic bag-of-words model
(scikit-learn) — lightweight and safe for any host. An alternative matching
backend uses on-device sentence-transformer embeddings for **semantic
matching** (ranking by meaning, so "ML" ≈ "machine learning", "reactjs" ≈
"react") — **no external API calls, nothing leaves the machine**:

```bash
pip install -r requirements-semantic.txt   # pulls in PyTorch (needs ~1-2 GB RAM)
python build_embeddings.py                  # precompute job embeddings (once)
# set USE_SEMANTIC=1 in your .env, then run the app
```

This is **off by default** and gated by the `USE_SEMANTIC` flag, so low-memory
hosts (like Render's free tier) automatically fall back to the classic matcher
and never load PyTorch.

## ☁️ Deploy to Render

This repo includes a `render.yaml` blueprint, so deployment is one click:

1. Push this project to a GitHub repo.
2. Go to **https://render.com** → **New** → **Blueprint**, and select your repo.
   Render reads `render.yaml` and provisions a free web service running
   `gunicorn app:app`.
3. In the service's **Environment** tab, add your two secrets:
   `ADZUNA_APP_ID` and `ADZUNA_APP_KEY`. (They are marked `sync: false` in the
   blueprint so they're never committed.)
4. Deploy. Your app will be live at `https://<your-app>.onrender.com`.

Notes:
- The `.env` file is git-ignored and is **not** used in production — set the
  keys as Render environment variables instead.
- On the free tier the service sleeps after inactivity, so the first request
  after idle takes ~30–60s to wake (cold start). Paid tiers stay warm.

## 🚀 Future Improvements

- Automated CI (run the pytest suite on every push)
- User accounts & saved jobs (would need a database — currently stateless)
- "Top in-demand skills" trends aggregated across searches, not just per-search
- Higher-fidelity resume parsing (structured section detection, not just keyword matching)
- Multi-page live search fetched incrementally further than the current on-demand pagination
