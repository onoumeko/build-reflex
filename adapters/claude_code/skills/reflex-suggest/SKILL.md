---
name: reflex-suggest
description: >
  Find reflexification opportunities by scanning the hook log. Shows two lists:
  (1) inputs that almost matched a reflex (schema_miss patterns) and (2) skills
  called >=3 times with zero reflex hits — full LLM cost that scripts could
  save. Triggers: "/reflex-suggest", "what should I reflexify", "find reflex
  opportunities".
license: MIT
---

# reflex-suggest

When invoked, run:

```bash
python3 /root/.claude/plugins/cache/build-reflex/build-reflex/0.1.0/core/reflex_suggest.py --days 7
```

Show output verbatim. For longer windows, pass `--days 30` or `--days 0` (all
time).

This skill is not a reflex — picking what to reflexify is a judgment call.
The script just surfaces the candidates by counting log entries.
