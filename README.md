# build-reflex

> Skip the LLM when a script will do.

A [Claude Code](https://docs.anthropic.com/claude/docs/claude-code) plugin
that lets you replace deterministic skill work with sibling Python scripts
("reflexes"). A `PreToolUse` hook intercepts Skill calls, validates the args
against a JSON-schema contract in the skill's frontmatter, runs the script,
and returns its stdout as the tool result — **the LLM never sees the call**.

## Why

The original pitch is "save tokens," but the real wins are:

1. **Reliable** — same input, same output. Deterministic tasks (count lines,
   hash a file, convert units) stop failing on model drift.
2. **Fast** — `~30 ms` subprocess vs `~4 s` LLM round trip. 100× on hot paths.
3. **Cheap** — zero tokens spent on work that didn't need a model.

Pure reflexes get a transparent on-disk LRU cache. Identical calls become free.

## Validated by research

The "deterministic execution, LLM only for bounded sub-tasks" pattern is backed
by independent academic work:

- **Blueprint First, Model Second** ([arxiv 2508.02721](https://arxiv.org/abs/2508.02721))
  — On the same Claude Sonnet 4 backbone, *Source Code Agent* (the same idea:
  codify workflow as a deterministic blueprint, invoke LLM as a tool, never let
  it decide the path) achieved **+97.6% final pass rate**, **-96% constraint
  violations** (11 vs 275), and **-27% execution steps** (10.2 vs 14.0) on
  TravelPlanner. Results transferred to production incident-diagnosis
  deployments.
- **Schema First Tool APIs** ([arxiv 2603.13404](https://arxiv.org/abs/2603.13404))
  — A controlled study confirming that JSON Schema contracts improve tool
  interface adherence, while identifying semantic misuse and timeout-sensitive
  tasks as the remaining bottlenecks. build-reflex's `semantic_preconditions`
  and `negative_examples` fields are designed to address exactly these gaps.

build-reflex is an open-source implementation of the same principle —
deterministic contracts, agent-free execution, zero tokens for work that
doesn't need a model.

## Install

This is a local marketplace. Add it to `~/.claude/settings.json`:

```json
{
  "extraKnownMarketplaces": {
    "build-reflex": {
      "source": {
        "source": "github",
        "repo": "onoumeko/build-reflex"
      }
    }
  },
  "enabledPlugins": {
    "build-reflex@build-reflex": true
  }
}
```

Restart Claude Code. The hook auto-registers; the bundled skills appear.

## What's in the box

| Skill | Purpose |
|---|---|
| **`utils`** | 8 zero-config reflexes — `file-hash`, `count-lines`, `b64-encode/decode`, `json-path`, `regex-extract`, `date-add`, `unit-convert`. Routed by input schema. |
| **`build-reflex`** | Audit one of your other skills, classify each section, scaffold reflex contract + `.py` stub. Per-candidate approval — never auto-decides boundaries. |
| **`reflex-stats`** | `/reflex-stats` — hits, fallback rate, estimated tokens & latency saved, top reflexes. |
| **`reflex-suggest`** | `/reflex-suggest` — reverse audit: which skills are burning tokens that scripts could save. |

Architecture:

```
spec/                         Reflex contract spec (v1) + templates
core/                         Runtime — validator, cache, drift, lint, stats, suggest
adapters/claude_code/         Claude Code hook + skills
```

All stdlib + PyYAML. No `pip install` needed.

## How it works

```
LLM calls Skill "utils" with {path: "/etc/hosts"}
   │
   ▼
PreToolUse hook fires
   │
   │  • Locate skills/utils/SKILL.md
   │  • Parse frontmatter, find a `reflexes:` list
   │  • Try each input_schema in order; first match wins → count-lines
   │  • Drift check: CONTRACT in script must hash-match the SKILL.md block
   │  • Cache hit? Return cached stdout, 0 ms.
   │  • Else: subprocess python3 count-lines.py with args on stdin, timeout enforced
   │  • Validate stdout against output_schema
   │
   ▼
Return script stdout as the tool result. LLM never loaded the SKILL.md body.

On any failure (script error, schema miss, timeout, drift) → fall through to
the LLM, plus inject a system-reminder so the model knows a reflex was tried.
```

## Contract reference

Embed in any SKILL.md frontmatter. Single (`reflex:`) or many (`reflexes:` list).

```yaml
reflex:
  reflex_id:        count-lines       # required, kebab-case
  source_skill_id:  utils             # required, matches SKILL.md `name:`
  version:          "0.1.0"           # required
  contract_version: "1"               # required

  input_schema:                       # required, JSON Schema subset
    type: object
    properties:
      path: { type: string }
    required: [path]
    additionalProperties: false

  output_schema:                      # required
    type: object
    properties:
      lines: { type: integer }
      bytes: { type: integer }
    required: [lines, bytes]
    additionalProperties: false

  timeout_seconds: 10                 # subprocess-enforced, default 10
  determinism:     pure               # pure | external_api | impure (pure → cached)
  on_failure:      fallback_to_agent  # default. or: hard_fail | retry_once
  side_effects:    []                 # advisory

  examples:                           # required, ≥1, drives --selfcheck
    - input:  { path: "/etc/hostname" }
      output: { lines: 1, bytes: 24 }
```

Supported schema keywords (intentional subset): `type`, `properties`,
`required`, `enum`, `items`, `additionalProperties`, `minimum`, `maximum`,
`pattern`. Anything else → schema miss → hook falls through.

## When something IS NOT a reflex

The `build-reflex` skill applies a 5-point gate. **All five must pass:**

1. Input fits a closed JSON schema (no free-text bag).
2. Output is a value, not a judgment call.
3. No judgment — same input → same output.
4. Failure modes are enumerable (file missing, bad format, timeout).
5. No skill chaining mid-execution.

Plus a frequency gate: scripts that run once a month aren't worth the file.

## Authoring a new reflex

```
$ # In Claude Code:
$ /build-reflex <some-skill-name>
```

The audit produces a table of AGENT / REFLEX-CANDIDATE / GRAY sections. You
approve each candidate; build-reflex generates the `reflex:` block and a
`<reflex_id>.py` skeleton. Implement `run(args)`, then:

```bash
python3 path/to/<reflex_id>.py --selfcheck   # validates against examples
python3 path/to/<reflex_id>.py --bench       # p50/p99 over 1000 runs
```

## Stats

```
$ /reflex-stats
reflex stats — last 7 day(s)
----------------------------------------
  hits          : 247  (89 from cache)
  fallbacks     : 8    (3.2%)
  tokens saved  : ~341,200
  latency saved : ~16.3 min
  ...
```

## Out of scope (v0.1)

- Real sandboxing (bwrap / firejail / container). `timeout_seconds` is the
  only enforced constraint. String-pattern "sandboxes" are theatre — we don't
  pretend.
- Natural-language router (Haiku-tier classifier turning "how many lines" into
  `{reflex_id, args}`). Planned for v1.0.
- Cross-skill imports — a reflex is one file with stdlib.

## License

MIT. See `LICENSE`.
