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
}

def run(args):
    return {"text": base64.b64decode(args["b64"]).decode("utf-8")}

if __name__ == "__main__":
    if "--selfcheck" in sys.argv:
        assert run({"b64": "aGVsbG8="}) == {"text": "hello"}
        print("ok")
    else:
        try: json.dump(run(json.loads(sys.stdin.read() or "{}")), sys.stdout)
        except Exception as e: print(f"err: {e}", file=sys.stderr); sys.exit(1)
