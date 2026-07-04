"""Local semantic embedding model (no external API calls at inference).

Uses a sentence-transformers model that runs fully on-device. The model files
are downloaded once from Hugging Face and cached locally; after that, encoding
happens offline.
"""

import os
from functools import lru_cache

MODEL_NAME = "all-MiniLM-L6-v2"  # 384-dim, fast, strong general-purpose model


def is_enabled():
    """Semantic mode is opt-in via the USE_SEMANTIC env var (default off).

    It stays off on small/free hosts so the app runs the lightweight classic
    matcher and never loads PyTorch.
    """
    return os.getenv("USE_SEMANTIC", "0").lower() in ("1", "true", "on", "yes")


@lru_cache(maxsize=1)
def available():
    """True only if semantic mode is enabled AND the library imports.

    Checked once at startup. Falls back gracefully (returns False) if
    sentence-transformers isn't installed on this host.
    """
    if not is_enabled():
        return False
    try:
        import sentence_transformers  # noqa: F401
        return True
    except Exception:
        return False


@lru_cache(maxsize=1)
def get_model():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(MODEL_NAME)


def embed(texts):
    """Encode a list of strings into L2-normalized vectors (cosine = dot)."""
    return get_model().encode(
        list(texts),
        normalize_embeddings=True,
        convert_to_numpy=True,
    )


def scale_similarity(cos):
    """Map a raw cosine similarity into a friendly 0..1 match strength.

    Sentence-transformer cosines for relevant text pairs sit roughly in the
    0.1–0.6 band, so we stretch that into 0–1 for a readable match %.
    """
    return max(0.0, min((float(cos) - 0.10) / 0.50, 1.0))
