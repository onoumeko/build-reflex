#!/usr/bin/env python3
"""Reflex: file-hash. Compute hash of file contents."""
import hashlib, json, os, sys

CONTRACT = {
    "reflex_id": "file-hash",
    "input_schema": {"type": "object",
                     "properties": {"path": {"type": "string"},
                                    "algo": {"type": "string", "enum": ["sha256", "sha1", "md5"]}},
                     "required": ["path", "algo"], "additionalProperties": False},
    "output_schema": {"type": "object",
                      "properties": {"hash": {"type": "string"}, "algo": {"type": "string"},
                                     "bytes": {"type": "integer"}},
                      "required": ["hash", "algo", "bytes"], "additionalProperties": False},
    "version": "0.1.0",
    "negative_examples": [
        {"input": {"path": "/definitely/does/not/exist/xyz", "algo": "sha256"}},
        {"input": {"path": "/etc/hostname", "algo": "crc32"}},
    ],
}

VALID_ALGOS = {"sha256", "sha1", "md5"}

def run(args):
    algo = args["algo"]
    if algo not in VALID_ALGOS:
        raise ValueError(f"algo must be one of {sorted(VALID_ALGOS)}, got {algo!r}")
    h = hashlib.new(algo)
    n = 0
    with open(args["path"], "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk); n += len(chunk)
    return {"hash": h.hexdigest(), "algo": algo, "bytes": n}

def _selfcheck():
    # positive
    p = "/tmp/reflex-test-hash.txt"
    open(p, "w").write("hello")
    r = run({"path": p, "algo": "sha256"})
    assert r["hash"] == "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824", r
    assert r["bytes"] == 5
    # negatives must raise
    for i, ex in enumerate(CONTRACT["negative_examples"]):
        try:
            run(ex["input"])
            print(f"FAIL negative {i}: expected raise", file=sys.stderr); sys.exit(1)
        except Exception: pass
    print("ok")

if __name__ == "__main__":
    if "--selfcheck" in sys.argv:
        _selfcheck()
    else:
        try: json.dump(run(json.loads(sys.stdin.read() or "{}")), sys.stdout)
        except Exception as e: print(f"err: {e}", file=sys.stderr); sys.exit(1)
