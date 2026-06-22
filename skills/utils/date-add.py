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
}

def run(args):
    # fromisoformat handles "YYYY-MM-DD" and full "YYYY-MM-DDTHH:MM:SS".
    d = datetime.fromisoformat(args["date"])
    d2 = d + timedelta(days=args.get("days", 0),
                       hours=args.get("hours", 0),
                       minutes=args.get("minutes", 0))
    # Preserve "date only" if input was date only.
    s = d2.isoformat() if d.time() != d.replace(hour=0, minute=0, second=0, microsecond=0).time() or "T" in args["date"] else d2.date().isoformat()
    return {"date": s}

if __name__ == "__main__":
    if "--selfcheck" in sys.argv:
        assert run({"date": "2026-01-01", "days": 30}) == {"date": "2026-01-31"}
        assert run({"date": "2026-01-01T00:00:00", "hours": 36}) == {"date": "2026-01-02T12:00:00"}
        print("ok")
    else:
        try: json.dump(run(json.loads(sys.stdin.read() or "{}")), sys.stdout)
        except Exception as e: print(f"err: {e}", file=sys.stderr); sys.exit(1)
