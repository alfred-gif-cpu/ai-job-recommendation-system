import pandas as pd

FILE_PATH = r"D:\Dataset\archive\job_summary.csv"

print("Reading dataset...")

df = pd.read_csv(FILE_PATH, nrows=50000, low_memory=False)

print("Columns found:")
print(df.columns)

# ==========================
# USE REAL COLUMNS
# ==========================

df = df[["job_link", "job_summary"]]

# remove empty rows
df = df.dropna()

# lowercase
df["job_summary"] = df["job_summary"].astype(str).str.lower()

# sample small dataset
df = df.sample(2000, random_state=42)

df.to_csv("jobs_small.csv", index=False)

print("✅ Saved jobs_small.csv")