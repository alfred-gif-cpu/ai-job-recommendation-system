# 🚀 AI Job Recommendation System

An AI-powered web application that recommends jobs based on user skills or uploaded resumes.

The system uses NLP-based skill extraction and cosine similarity to match candidates with relevant job opportunities. It also includes India-aware ranking to prioritize Indian job listings.

## ✨ Features

- 📄 Resume PDF upload and skill extraction
- 🧠 NLP-based skill detection
- 🤖 AI job matching using cosine similarity
- 🔴 Real-time job search via the Adzuna API (with safe CSV fallback)
- 🔗 Real job titles, companies & one-click "Apply / View Job" links
- 🎯 "Skills to Learn" gap analysis + matched/required skill meter per job
- 🔍 Match-breakdown tooltip on each score ring
- 🇮🇳 India-aware recommendation ranking
- 🌗 Dark / light theme toggle, sort & filter, "Show more" pagination
- 🔗 Shareable results links + recent-search history
- 🎨 Ultra-premium modern UI (glassmorphism design)
- 📊 Match score visualization (capped at 100%)
- 🛡️ Graceful handling of empty input, non-PDF/scanned files & no-match cases

## 🛠 Tech Stack

- Python
- Flask
- Scikit-learn
- Pandas
- PyPDF2
- HTML / CSS

## 📌 How it Works

1. User enters skills or uploads resume
2. Skills are extracted using NLP
3. Job descriptions are vectorized
4. Cosine similarity calculates best matches
5. Results shown with match percentage and missing skills

## ▶️ Run Locally

```bash
pip install -r requirements.txt
python app.py
# open http://localhost:10000
```

## 🔴 Real-time jobs (Adzuna)

Flip the **Live jobs** toggle to search real, current openings across India via
the free [Adzuna API](https://developer.adzuna.com/). Pick a **city**
(Bangalore, Hyderabad, Mumbai, Pune, Delhi, Remote, … or All India), and each
result shows its **salary range** in ₹ where available. Results can be filtered
(Remote / With-salary) and sorted by salary, and your last city + filter are
remembered. Responses are cached in-memory for 10 minutes to keep repeat
searches fast.

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

- Real-time job API integration
- User accounts & saved jobs
- Dashboard analytics
- LLM-based recommendation explanations
- TF-IDF / embedding-based matching for higher relevance
