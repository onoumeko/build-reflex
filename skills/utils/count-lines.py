#!/usr/bin/env python3
"""Reflex: count-lines. Count lines and bytes of a file."""
import json, sys

CONTRACT = {
    "reflex_id": "count-lines",
    "input_schema": {"type": "object", "properties": {"path": {"type": "string"}},
                     "required": ["path"], "additionalProperties": False},
    "output_schema": {"type": "object",
                      "properties": {"lines": {"type": "integer"}, "bytes": {"type": "integer"}},
                      "required": ["lines", "bytes"], "additionalProperties": False},
    "version": "0.1.0",
}

def run(args):
    lines = bytes_ = 0
    with open(args["path"], "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            lines += chunk.count(b"\n"); bytes_ += len(chunk)
    return {"lines": lines, "bytes": bytes_}

if __name__ == "__main__":
    if "--selfcheck" in sys.argv:
        p = "/tmp/reflex-test-lines.txt"; open(p, "w").write("a\nb\nc\n")
        assert run({"path": p}) == {"lines": 3, "bytes": 6}
        print("ok")
    else:
        try: json.dump(run(json.loads(sys.stdin.read() or "{}")), sys.stdout)
        except Exception as e: print(f"err: {e}", file=sys.stderr); sys.exit(1)
