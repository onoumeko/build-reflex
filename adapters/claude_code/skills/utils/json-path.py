#!/usr/bin/env python3
"""Reflex: json-path. Dotted path access: a.b[0].c → walks dict keys and list indexes."""
import json, re, sys

CONTRACT = {
    "reflex_id": "json-path",
    "input_schema": {"type": "object",
                     "properties": {"json": {"type": "string"}, "path": {"type": "string"}},
                     "required": ["json", "path"], "additionalProperties": False},
    "output_schema": {"type": "object", "properties": {"value": {}},
                      "required": ["value"], "additionalProperties": False},
    "version": "0.1.0",
    "negative_examples": [
        {"input": {"json": "not json at all", "path": "a.b"}},
        {"input": {"json": '{"a":1}', "path": "missing.key"}},
    ],
}

_TOKEN = re.compile(r"\.?([^.\[\]]+)|\[(\d+)\]")

def _walk(obj, path):
    cur = obj
    for m in _TOKEN.finditer(path):
        key, idx = m.group(1), m.group(2)
        if idx is not None:
            cur = cur[int(idx)]
        else:
            cur = cur[key]
    return cur

def run(args):
    return {"value": _walk(json.loads(args["json"]), args["path"])}

def _selfcheck():
    assert run({"json": '{"a":{"b":[10,20]}}', "path": "a.b[1]"}) == {"value": 20}
    assert run({"json": '[1,{"x":"y"}]', "path": "[1].x"}) == {"value": "y"}
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
