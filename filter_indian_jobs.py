import pandas as pd

# load current dataset
df = pd.read_csv("jobs_with_skills.csv")

# keywords representing indian jobs
india_keywords = [
    "india",
    "bangalore",
    "bengaluru",
    "hyderabad",
    "chennai",
    "pune",
    "mumbai",
    "gurgaon",
    "noida",
    "delhi",
    "remote india"
]

# combine keywords into pattern
pattern = "|".join(india_keywords)

# filter using job_summary text
india_df = df[
    df["job_summary"].str.contains(pattern, case=False, na=False)
]

print("Indian jobs found:", india_df.shape)

# save new dataset
india_df.to_csv("india_jobs_with_skills.csv", index=False)

print("✅ Saved india_jobs_with_skills.csv")