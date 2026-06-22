#!/usr/bin/env python3
"""Reflex: b64-decode."""
import base64, json, sys

CONTRACT = {
    "reflex_id": "b64-decode",
    "input_schema": {"type": "object", "properties": {"b64": {"type": "string"}},
                     "required": ["b64"], "additionalProperties": False},
    "output_schema": {"type": "object", "properties": {"text": {"type": "string"}},
                      "required": ["text"], "additionalProperties": False},
    "version": "0.1.0",
    "negative_examples": [{"input": {"b64": "this is not valid base64 !!!"}}],
}

def run(args):
    # validate=True rejects non-base64 characters; default base64.b64decode silently ignores them.
    return {"text": base64.b64decode(args["b64"], validate=True).decode("utf-8")}

def _selfcheck():
    assert run({"b64": "aGVsbG8="}) == {"text": "hello"}
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
