#!/usr/bin/env python3
"""Reflex: date-add. ISO 8601 date arithmetic (days/hours/minutes)."""
import json, sys
from datetime import datetime, timedelta

CONTRACT = {
    "reflex_id": "date-add",
    "input_schema": {"type": "object",
                     "properties": {"date": {"type": "string"},
                                    "days": {"type": "integer"},
                                    "hours": {"type": "integer"},
                                    "minutes": {"type": "integer"}},
                     "required": ["date"], "additionalProperties": False},
    "output_schema": {"type": "object", "properties": {"date": {"type": "string"}},
                      "required": ["date"], "additionalProperties": False},
    "version": "0.1.0",
    "negative_examples": [{"input": {"date": "not a date", "days": 1}}],
}

def run(args):
    # fromisoformat raises ValueError on garbage — natural negative-example trigger.
    d = datetime.fromisoformat(args["date"])
    d2 = d + timedelta(days=args.get("days", 0),
                       hours=args.get("hours", 0),
                       minutes=args.get("minutes", 0))
    # Preserve "date only" if input was date only.
    has_time = "T" in args["date"]
    s = d2.isoformat() if has_time else d2.date().isoformat()
    return {"date": s}

def _selfcheck():
    assert run({"date": "2026-01-01", "days": 30}) == {"date": "2026-01-31"}
    assert run({"date": "2026-01-01T00:00:00", "hours": 36}) == {"date": "2026-01-02T12:00:00"}
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
