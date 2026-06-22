#!/usr/bin/env python3
"""Analyze /tmp/reflex-intercept.log to suggest reflexification candidates.

Output a ranked list of:
  1. schema_miss patterns — args that almost matched a reflex but missed
  2. skills frequently called that have NO reflex at all (zero hits)

Usage: python3 reflex_suggest.py [--days N]
"""
import argparse
import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

LOG = Path("/tmp/reflex-intercept.log")


def load(days):
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


def report(events):
    schema_miss = Counter()
    by_skill_status = defaultdict(Counter)
    for e in events:
        by_skill_status[e.get("skill", "?")][e.get("status", "?")] += 1
        if e.get("status") == "schema_miss":
            err = e.get("err", "")
            schema_miss[(e.get("skill"), err[:80])] += 1

    out = []
    out.append("reflex-suggest — opportunities to reflexify\n")

    # frequently schema-missed: candidate for adding/loosening a reflex
    if schema_miss:
        out.append("[1] Inputs that almost matched a reflex (consider adding one):\n")
        for (skill, err), cnt in schema_miss.most_common(10):
            out.append(f"   {cnt:4d}×  skill={skill}  {err}")
        out.append("")

    # skills called but with no reflex hits — full LLM cost
    pure_agent = []
    for skill, statuses in by_skill_status.items():
        hits = statuses.get("ok", 0) + statuses.get("cache_hit", 0)
        total = sum(statuses.values())
        if total >= 3 and hits == 0:
            pure_agent.append((skill, total))
    if pure_agent:
        pure_agent.sort(key=lambda x: -x[1])
        out.append("[2] Skills run >=3 times this window with ZERO reflex hits:")
        out.append("    (these are spending tokens that scripts could save)\n")
        for skill, n in pure_agent[:10]:
            out.append(f"   {n:4d}×  /build-reflex {skill}")
        out.append("")

    if not schema_miss and not pure_agent:
        out.append("No actionable patterns found. Either no log data yet, or every")
        out.append("frequently-called skill already has a working reflex.")

    return "\n".join(out)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--days", type=int, default=7, help="0 = all time")
    args = p.parse_args()
    print(report(load(args.days)))


if __name__ == "__main__":
    main()