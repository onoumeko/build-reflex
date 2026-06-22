---
name: reflex-stats
description: >
  Show how much the reflex layer has saved (token/latency estimates, hit rate,
  top reflexes, fallback rate). Reads /tmp/reflex-intercept.log. Triggers:
  "reflex stats", "/reflex-stats", "how much have reflexes saved".
license: MIT
---

# reflex-stats

When invoked, run:

```bash
python3 /root/.claude/plugins/cache/build-reflex/build-reflex/0.1.0/lib/reflex_stats.py --days 7
```

Show the output to the user verbatim. If they ask for a longer window, pass
`--days 30` or `--days 0` (all time). If they want raw JSON, pass `--json`.

This skill is intentionally not a reflex — the stats output is for humans, and
running it through the reflex layer would be ouroboric.
