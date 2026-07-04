"""Offline: precompute semantic embeddings for the India job dataset.

Run once (and whenever the dataset changes):

    python build_embeddings.py

It writes ``job_embeddings.npy`` aligned row-for-row with the cleaned dataset,
so the web app never has to embed the whole corpus at startup.
"""

import numpy as np
import pandas as pd

from semantic import embed

DATASET = "jobs_with_skills.csv"
OUT = "job_embeddings.npy"


def load_jobs():
    df = pd.read_csv(DATASET).dropna(subset=["skills"]).reset_index(drop=True)
    return df


def job_text(row):
    """Skill-focused text: canonical skills first, then a summary snippet."""
    skills = str(row["skills"])
    summary = str(row["job_summary"])[:300]
    return f"Skills: {skills}. {summary}"


if __name__ == "__main__":
    df = load_jobs()
    print(f"Embedding {len(df)} jobs from {DATASET} ...")
    texts = df.apply(job_text, axis=1).tolist()
    emb = embed(texts).astype("float32")
    np.save(OUT, emb)
    print(f"Saved {OUT} with shape {emb.shape}")
