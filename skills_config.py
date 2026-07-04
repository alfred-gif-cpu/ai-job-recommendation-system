import re

# -----------------------------
# MASTER SKILL LIST
# Shared by the CSV recommender, the resume parser and the live API scorer.
# -----------------------------
SKILL_LIST = [
    "python", "java", "c++", "sql", "mysql", "postgresql",
    "machine learning", "deep learning", "nlp",
    "tensorflow", "pytorch", "pandas", "numpy", "scikit-learn",
    "flask", "django", "fastapi", "rest api", "api",
    "javascript", "typescript", "react", "angular", "node.js",
    "html", "css", "bootstrap",
    "aws", "azure", "gcp", "docker", "kubernetes",
    "git", "linux", "excel", "powerbi", "tableau",
    "spark", "hadoop", "mongodb", "redis",
    "communication", "leadership", "problem solving",
]


def extract_skills(text):
    """Return the master-list skills found as whole words in ``text``."""
    text = str(text).lower()
    return [s for s in SKILL_LIST if re.search(r"\b" + re.escape(s) + r"\b", text)]
