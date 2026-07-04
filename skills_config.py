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


# Common aliases / spellings mapped to their canonical skill. Kept conservative
# to avoid false positives (e.g. no bare "go" or "r").
SKILL_ALIASES = {
    "ml": "machine learning",
    "machine-learning": "machine learning",
    "dl": "deep learning",
    "deep-learning": "deep learning",
    "js": "javascript",
    "ts": "typescript",
    "reactjs": "react",
    "react.js": "react",
    "nodejs": "node.js",
    "node js": "node.js",
    "k8s": "kubernetes",
    "postgres": "postgresql",
    "mongo": "mongodb",
    "sklearn": "scikit-learn",
    "scikit learn": "scikit-learn",
    "cpp": "c++",
    "power bi": "powerbi",
    "power-bi": "powerbi",
    "tensor flow": "tensorflow",
    "problem-solving": "problem solving",
}

# Precompile a matcher per skill/alias. We bound each term with alphanumeric
# look-arounds instead of \b so terms ending/starting in punctuation (e.g.
# "c++") still match — \b never matches after a "+".
def _bounded(term):
    return re.compile(r"(?<![a-z0-9])" + re.escape(term) + r"(?![a-z0-9])")


_PATTERNS = [(skill, _bounded(skill)) for skill in SKILL_LIST]
_PATTERNS += [(canonical, _bounded(alias)) for alias, canonical in SKILL_ALIASES.items()]


def extract_skills(text):
    """Return the canonical master-list skills found in ``text``.

    Matches whole tokens (so "react" != "reaction") and resolves common
    aliases ("ml" -> machine learning, "k8s" -> kubernetes, ...). Results are
    de-duplicated and returned in master-list order.
    """
    text = str(text).lower()
    found = {skill for skill, pat in _PATTERNS if pat.search(text)}
    return [skill for skill in SKILL_LIST if skill in found]
