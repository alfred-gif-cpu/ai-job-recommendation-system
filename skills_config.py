import re
from urllib.parse import quote_plus

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
    # --- languages ---
    "golang", "rust", "kotlin", "swift", "php", "scala", "ruby",
    # --- frontend ---
    "next.js", "vue", "svelte", "tailwind",
    # --- cloud / devops ---
    "terraform", "jenkins", "ansible", "ci/cd", "github actions",
    # --- data engineering ---
    "airflow", "kafka", "snowflake", "databricks",
    # --- modern ai / ml ---
    "keras", "opencv", "huggingface", "generative ai", "llm",
    "computer vision", "transformers", "langchain",
    # --- databases ---
    "elasticsearch", "dynamodb", "sqlite", "oracle", "cassandra",
    # --- testing ---
    "selenium", "junit", "pytest", "cypress",
    # --- mobile ---
    "android", "ios", "flutter", "react native",
    # --- other ---
    "graphql", "microservices", "agile", "scrum", "jira", "figma", "ui/ux design",
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
    "nextjs": "next.js",
    "next js": "next.js",
    "vuejs": "vue",
    "vue.js": "vue",
    "tailwindcss": "tailwind",
    "tailwind css": "tailwind",
    "ci-cd": "ci/cd",
    "ci cd": "ci/cd",
    "continuous integration": "ci/cd",
    "gen ai": "generative ai",
    "genai": "generative ai",
    "generative-ai": "generative ai",
    "large language model": "llm",
    "large language models": "llm",
    "hugging face": "huggingface",
    "react-native": "react native",
    "ui/ux": "ui/ux design",
    "ux/ui": "ui/ux design",
    "ui ux": "ui/ux design",
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


_REMOTE_SENSING_RE = re.compile(r"remote[\s-]*sensing")
_WFH_RE = re.compile(r"\bwfh\b")


def is_remote_text(*parts):
    """Whether the given text(s) describe a remote/work-from-home job.

    Uses substring matching (so "remotely", "remote-friendly" etc. still
    count), but first strips "remote sensing" mentions — a real engineering
    discipline (satellites/GIS) that would otherwise be mislabeled as a
    remote-work job.
    """
    text = " ".join(str(p) for p in parts if p).lower()
    text = _REMOTE_SENSING_RE.sub(" ", text)
    return "remote" in text or "work from home" in text or bool(_WFH_RE.search(text))


def learn_link(skill):
    """A stable "learn this skill" link: a YouTube search for tutorials.

    Generated from the skill name rather than hand-curated per-skill URLs, so
    it can never go stale or 404 and needs no maintenance as the skill list
    grows.
    """
    query = quote_plus(f"{skill} tutorial for beginners")
    return f"https://www.youtube.com/results?search_query={query}"
