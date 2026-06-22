"""On-disk LRU cache for pure reflexes. SQLite for atomic concurrent access."""
import hashlib
import json
import sqlite3
import time

CACHE_PATH = "/tmp/reflex-cache.sqlite3"
MAX_ENTRIES = 1000


def _conn():
    c = sqlite3.connect(CACHE_PATH, timeout=1)
    c.execute("CREATE TABLE IF NOT EXISTS cache(k TEXT PRIMARY KEY, v TEXT, t REAL)")
    return c


def _key(reflex_id, args):
    payload = reflex_id + "::" + json.dumps(args, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def get(reflex_id, args):
    try:
        with _conn() as c:
            row = c.execute("SELECT v FROM cache WHERE k=?", (_key(reflex_id, args),)).fetchone()
            if row:
                # bump access time for LRU
                c.execute("UPDATE cache SET t=? WHERE k=?", (time.time(), _key(reflex_id, args)))
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
    # one runnable check
    clear()
    assert get("test", {"x": 1}) is None
    put("test", {"x": 1}, '{"y": 2}')
    assert get("test", {"x": 1}) == '{"y": 2}'
    assert get("test", {"x": 2}) is None  # different args, different key
    clear()
    print("ok")
