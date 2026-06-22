#!/usr/bin/env python3
"""Summarize /tmp/reflex-intercept.log into hit counts, savings, fallback rates.

Run: python3 reflex_stats.py [--days N] [--json]
"""
import argparse
import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

LOG = Path("/tmp/reflex-intercept.log")

# Conservative average for an LLM round trip handling a skill call.
ASSUMED_AGENT_LATENCY_MS = 4000


def parse_lines(days):
    cutoff = time.time() - days * 86400 if days else 0
    if not LOG.exists():
        return []
    out = []
    for line in LOG.read_text().splitlines():
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        ts = ev.get("t", "")
        try:
            t = time.mktime(time.strptime(ts, "%Y-%m-%dT%H:%M:%S"))
        except ValueError:
            t = 0
        if t >= cutoff:
            out.append(ev)
    return out


def summarize(events):
    total = len(events)
    by_status = Counter(e.get("status", "?") for e in events)
    by_reflex = Counter(e.get("reflex_id") for e in events if e.get("reflex_id"))
    hits = by_status.get("ok", 0) + by_status.get("cache_hit", 0)
    cache_hits = by_status.get("cache_hit", 0)
    falls = by_status.get("fail", 0) + by_status.get("drift", 0)
    saved_tokens = sum(e.get("saved_tokens", 0) for e in events
                       if e.get("status") in ("ok", "cache_hit"))
    reflex_ms = sum(e.get("dur_ms", 0) for e in events
                    if e.get("status") in ("ok", "cache_hit"))
    saved_ms = max(0, hits * ASSUMED_AGENT_LATENCY_MS - reflex_ms)
    fallback_rate = (falls / total * 100) if total else 0
    return {
        "total_events": total,
        "hits": hits,
        "cache_hits": cache_hits,
        "fallbacks": falls,
        "fallback_rate_pct": round(fallback_rate, 1),
        "saved_tokens_est": saved_tokens,
        "saved_latency_min_est": round(saved_ms / 60000, 1),
        "by_status": dict(by_status),
        "top_reflexes": by_reflex.most_common(10),
    }


def render(s, days):
    window = f"last {days} day(s)" if days else "all time"
    out = []
    out.append(f"reflex stats — {window}")
    out.append("-" * 40)
    out.append(f"  hits          : {s['hits']}  ({s['cache_hits']} from cache)")
    out.append(f"  fallbacks     : {s['fallbacks']}  ({s['fallback_rate_pct']}%)")
    out.append(f"  tokens saved  : ~{s['saved_tokens_est']:,}")
    out.append(f"  latency saved : ~{s['saved_latency_min_est']} min  (vs {ASSUMED_AGENT_LATENCY_MS}ms/call agent)")
    out.append("")
    out.append("  status breakdown:")
    for k, v in s["by_status"].items():
        out.append(f"    {k:14s} {v}")
    if s["top_reflexes"]:
        out.append("")
        out.append("  top reflexes:")
        for r, c in s["top_reflexes"]:
            out.append(f"    {r:24s} {c}")
    return "\n".join(out)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--days", type=int, default=7, help="0 = all time")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()
    events = parse_lines(args.days)
    s = summarize(events)
    if args.json:
        print(json.dumps(s, indent=2))
    else:
        print(render(s, args.days))


if __name__ == "__main__":
    main()
