import pandas as pd
import re

df = pd.read_csv("jobs_small.csv")

# BIGGER SKILL LIST (industry-level)
skill_list = [
    "python","java","c++","sql","mysql","postgresql",
    "machine learning","deep learning","nlp","tensorflow","pytorch",
    "pandas","numpy","scikit-learn","data analysis",
    "flask","django","fastapi","rest api","api",
    "javascript","typescript","react","angular","node.js",
    "html","css","bootstrap",
    "aws","azure","gcp","docker","kubernetes",
    "git","linux","excel","powerbi","tableau",
    "spark","hadoop","mongodb","redis",
    "communication","leadership","problem solving"
]

def extract_skills(text):
    text = str(text).lower()
    found = []

    for skill in skill_list:
        if re.search(r"\b" + re.escape(skill) + r"\b", text):
            found.append(skill)

    return ", ".join(found)

# extract
df["skills"] = df["job_summary"].apply(extract_skills)

# remove rows with no skills
df = df[df["skills"] != ""]

df.to_csv("jobs_with_skills.csv", index=False)

print("✅ Done! Total rows:", len(df))