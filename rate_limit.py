"""Tiny in-memory sliding-window rate limiter (no external dependency).

Good enough for a single-process free-tier deploy: protects the Adzuna free
quota from being drained by a runaway client or accidental request loop.
"""

import time
from collections import defaultdict, deque
from threading import Lock

_lock = Lock()
_hits = defaultdict(deque)


def allow(key, limit=20, window=60):
    """Return True if `key` has made fewer than `limit` calls in the last
    `window` seconds; records the call if allowed."""
    now = time.time()
    with _lock:
        q = _hits[key]
        while q and now - q[0] > window:
            q.popleft()
        if len(q) >= limit:
            return False
        q.append(now)
        return True


def client_ip(request):
    """Best-effort real client IP behind Render's reverse proxy."""
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.remote_addr or "unknown"
