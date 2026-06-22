"""On-disk LRU cache for pure reflexes. SQLite for atomic concurrent access.

File-mtime fingerprinting: if any arg value is a string pointing at an existing
file, that file's (path, mtime, size) is folded into the cache key. So a reflex
called with the same args after the file changed becomes a natural miss instead
of returning stale data. Non-existent paths and non-path strings are ignored —
no false invalidations.
"""
import hashlib
import json
import os
import sqlite3
import time

CACHE_PATH = "/tmp/reflex-cache.sqlite3"
MAX_ENTRIES = 1000


def _conn():
    c = sqlite3.connect(CACHE_PATH, timeout=1)
    c.execute("CREATE TABLE IF NOT EXISTS cache(k TEXT PRIMARY KEY, v TEXT, t REAL)")
    return c


def _file_fingerprint(args):
    """Walk args, return list of (path, mtime, size) for string values that
    name an existing regular file. Deterministic order."""
    out = []
    def walk(v):
        if isinstance(v, str):
            try:
                st = os.stat(v)
                if os.path.isfile(v):
                    out.append((v, st.st_mtime_ns, st.st_size))
            except (OSError, ValueError):
                pass
        elif isinstance(v, dict):
            for k in sorted(v):
                walk(v[k])
        elif isinstance(v, list):
            for x in v:
                walk(x)
    walk(args)
    return out


def _key(reflex_id, args):
    fp = _file_fingerprint(args)
    payload = json.dumps(
        {"id": reflex_id, "args": args, "fp": fp},
        sort_keys=True, separators=(",", ":"), default=str,
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def get(reflex_id, args):
    try:
        k = _key(reflex_id, args)
        with _conn() as c:
            row = c.execute("SELECT v FROM cache WHERE k=?", (k,)).fetchone()
            if row:
                c.execute("UPDATE cache SET t=? WHERE k=?", (time.time(), k))
                return row[0]
    except sqlite3.Error:
        pass
    return None


def put(reflex_id, args, value):
    try:
        with _conn() as c:
            c.execute("INSERT OR REPLACE INTO cache(k, v, t) VALUES(?, ?, ?)",
                      (_key(reflex_id, args), value, time.time()))
            n = c.execute("SELECT COUNT(*) FROM cache").fetchone()[0]
            if n > MAX_ENTRIES:
                c.execute("DELETE FROM cache WHERE k IN "
                          "(SELECT k FROM cache ORDER BY t LIMIT ?)", (n - MAX_ENTRIES,))
    except sqlite3.Error:
        pass


def clear():
    try:
        with _conn() as c:
            c.execute("DELETE FROM cache")
    except sqlite3.Error:
        pass


if __name__ == "__main__":
    clear()
    # basic put/get
    assert get("test", {"x": 1}) is None
    put("test", {"x": 1}, '{"y": 2}')
    assert get("test", {"x": 1}) == '{"y": 2}'
    assert get("test", {"x": 2}) is None

    # mtime fingerprinting: same args, file changed → cache miss
    p = "/tmp/reflex-cache-test.txt"
    open(p, "w").write("v1")
    put("file-reflex", {"path": p}, '{"size": 2}')
    assert get("file-reflex", {"path": p}) == '{"size": 2}'
    time.sleep(0.01)  # ensure mtime differs
    open(p, "w").write("v2 longer")
    assert get("file-reflex", {"path": p}) is None, "mtime change should invalidate"
    os.remove(p)

    # non-existent path: no false invalidation
    put("str-reflex", {"path": "/definitely/does/not/exist"}, '{"ok": true}')
    assert get("str-reflex", {"path": "/definitely/does/not/exist"}) == '{"ok": true}'

    # non-path string: no fingerprint, behaves normally
    put("text-reflex", {"text": "hello"}, '{"b64": "aGVsbG8="}')
    assert get("text-reflex", {"text": "hello"}) == '{"b64": "aGVsbG8="}'

    clear()
    print("ok")
