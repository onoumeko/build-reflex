#!/usr/bin/env python3
"""Reflex: b64-encode."""
import base64, json, sys

CONTRACT = {
    "reflex_id": "b64-encode",
    "input_schema": {"type": "object", "properties": {"text": {"type": "string"}},
                     "required": ["text"], "additionalProperties": False},
    "output_schema": {"type": "object", "properties": {"b64": {"type": "string"}},
                      "required": ["b64"], "additionalProperties": False},
    "version": "0.1.0",
}

def run(args):
    return {"b64": base64.b64encode(args["text"].encode("utf-8")).decode("ascii")}

if __name__ == "__main__":
    if "--selfcheck" in sys.argv:
        assert run({"text": "hello"}) == {"b64": "aGVsbG8="}
        print("ok")
    else:
        try: json.dump(run(json.loads(sys.stdin.read() or "{}")), sys.stdout)
        except Exception as e: print(f"err: {e}", file=sys.stderr); sys.exit(1)
