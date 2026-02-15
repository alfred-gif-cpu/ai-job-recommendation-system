import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# ===============================
# LOAD DATASET
# ===============================
df = pd.read_csv("jobs_with_skills.csv")

# remove empty skills
df = df.dropna(subset=["skills"])

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
    "remote india"
]

# ===============================
# VECTORIZE SKILLS
# ===============================
vectorizer = CountVectorizer()
job_vectors = vectorizer.fit_transform(df["skills"])


# ===============================
# MAIN FUNCTION (USED BY FLASK)
# ===============================
def recommend_jobs(user_skills, top_n=5):

    user_skills = user_skills.lower()
    user_set = set([s.strip() for s in user_skills.split(",")])

    user_vector = vectorizer.transform([user_skills])

    similarity = cosine_similarity(user_vector, job_vectors)
    scores = similarity[0]

    results = []

    for i, score in enumerate(scores):

        if score > 0:

            summary = str(df.iloc[i]["job_summary"]).lower()

            # India preference bonus
            india_bonus = 0
            if any(word in summary for word in india_keywords):
                india_bonus = 0.15

            final_score = score + india_bonus

            job_skills = set(
                [s.strip() for s in df.iloc[i]["skills"].split(",")]
            )

            missing = job_skills - user_set

            results.append({
                "score": round(final_score * 100, 2),
                "india_job": india_bonus > 0,
                "skills": df.iloc[i]["skills"],
                "missing_skills": ", ".join(missing),
                "summary": df.iloc[i]["job_summary"][:150]
            })

    # sort by score
    results = sorted(
        results,
        key=lambda x: x["score"],
        reverse=True
    )

    return results[:top_n]