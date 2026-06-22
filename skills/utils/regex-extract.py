#!/usr/bin/env python3
"""Reflex: regex-extract. Return all matches (group 0 by default)."""
import json, re, sys

CONTRACT = {
    "reflex_id": "regex-extract",
    "input_schema": {"type": "object",
                     "properties": {"text": {"type": "string"}, "pattern": {"type": "string"},
                                    "group": {"type": "integer", "minimum": 0}},
                     "required": ["text", "pattern"], "additionalProperties": False},
    "output_schema": {"type": "object",
                      "properties": {"matches": {"type": "array", "items": {"type": "string"}}},
                      "required": ["matches"], "additionalProperties": False},
    "version": "0.1.0",
}

def run(args):
    g = args.get("group", 0)
    return {"matches": [m.group(g) for m in re.finditer(args["pattern"], args["text"])]}

if __name__ == "__main__":
    if "--selfcheck" in sys.argv:
        assert run({"text": "a1 b22 c333", "pattern": r"\d+"}) == {"matches": ["1", "22", "333"]}
        assert run({"text": "k=v;a=b", "pattern": r"(\w+)=(\w+)", "group": 2}) == {"matches": ["v", "b"]}
        print("ok")
    else:
        try: json.dump(run(json.loads(sys.stdin.read() or "{}")), sys.stdout)
        except Exception as e: print(f"err: {e}", file=sys.stderr); sys.exit(1)
