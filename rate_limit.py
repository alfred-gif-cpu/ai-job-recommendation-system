"""Tiny in-memory sliding-window rate limiter (no external dependency).

Good enough for a single-process free-tier deploy: protects the Adzuna free
quota from being drained by a runaway client or accidental request loop.
"""

import time
from collections import defaultdict, deque
from threading import Lock

_lock = Lock()
_hits = defaultdict(deque)
_call_count = 0


def allow(key, limit=20, window=60):
    """Return True if `key` has made fewer than `limit` calls in the last
    `window` seconds; records the call if allowed."""
    global _call_count
    now = time.time()
    with _lock:
        q = _hits[key]
        while q and now - q[0] > window:
            q.popleft()
        allowed = len(q) < limit
        if allowed:
            q.append(now)

        # Periodically drop keys whose deque has emptied out, so long-running
        # processes don't accumulate one entry per distinct caller forever.
        _call_count += 1
        if _call_count % 500 == 0:
            for k in [k for k, dq in _hits.items() if not dq]:
                del _hits[k]

        return allowed


def client_ip(request):
    """Best-effort real client IP behind Render's reverse proxy."""
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.remote_addr or "unknown"
