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


# Precompile a matcher per skill. We bound each skill with alphanumeric
# look-arounds instead of \b so skills ending/starting in punctuation (e.g.
# "c++") still match — \b never matches after a "+".
_SKILL_PATTERNS = [
    (skill, re.compile(r"(?<![a-z0-9])" + re.escape(skill) + r"(?![a-z0-9])"))
    for skill in SKILL_LIST
]


def extract_skills(text):
    """Return the master-list skills found as whole tokens in ``text``."""
    text = str(text).lower()
    return [skill for skill, pat in _SKILL_PATTERNS if pat.search(text)]
