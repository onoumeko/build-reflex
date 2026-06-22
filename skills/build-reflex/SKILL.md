---
name: build-reflex
displayName: 建立反射
description: >
  Audit an existing Claude Code skill and identify which parts can be replaced
  with deterministic Python "reflexes" — scripts the PreToolUse hook invokes
  instead of the LLM, saving tokens and context. Then scaffold those reflexes:
  embed a contract block in the target SKILL.md frontmatter and generate a
  sibling .py with a self-check. Trigger phrases: "建立反射", "build reflex",
  "reflex audit <skill>", "what in <skill> can become a script".
license: MIT
---

# 建立反射 (build-reflex)

You convert agent work into scripts where appropriate. You **never auto-replace**
anything. Each candidate is proposed to the user; the user approves per item;
only then do you generate.

## What a reflex is

A reflex is a sibling Python script next to a `SKILL.md`, invoked
automatically by a `PreToolUse` hook before the LLM ever loads the skill.
Contract lives in the target SKILL.md's YAML frontmatter under `reflex:`. The
hook validates input against the contract, runs the script, validates output,
and returns stdout as the tool result — the LLM never sees the call. On any
failure, the hook falls through and the LLM handles the skill normally.

## Five-point reflex criteria (ALL must pass)

A skill section / capability qualifies as a reflex candidate only if:

1. **Deterministic input** — args fit a closed JSON schema (no free-text bag).
2. **Deterministic output** — answer is a value, not a judgment call.
3. **No judgment** — same input → same output (or same-modulo-declared-side-effect for external APIs).
4. **Enumerable failures** — failure modes can be listed (file missing, bad format, timeout), not "the model decides what went wrong".
5. **No skill chaining** — execution does not need to call another skill or the LLM mid-stream.

Anything failing any of the five stays agent-layer. Passes 3+/5 but not all → **GRAY**, surface as gray, never auto-promote.

## Frequency gate

For every candidate, first ask "does this reflex need to exist at all?" If
the skill section is invoked once a month, scripting it saves no real tokens.
**Skip it**. The five criteria are necessary, not sufficient — frequency ×
token cost is the actual gate.

## `reflex_index` — progressive disclosure for LLMs

When you generate a reflex, also add a `reflex_index:` list to the target
SKILL.md frontmatter (under `description`). Each entry is a one-line summary
of the reflex's I/O contract:

```yaml
reflex_index:
  - "count-lines {path} → {lines, bytes}"
  - "file-hash {path, algo} → {hash, algo, bytes}"
```

The LLM sees this during the describing phase (before the full SKILL.md body
is loaded), so it can construct args matching the schema instead of guessing.
Higher hit rate, fewer schema misses.

## Workflow when invoked on `<target-skill>`

### A. Locate
Glob `/root/.claude/plugins/cache/*/*/*/skills/<target-skill>/SKILL.md`. If
none found, ask the user for the absolute path. Read it.

### B. Classify section-by-section
Walk the markdown by headers. For each section, tag **AGENT** / **REFLEX-CANDIDATE** / **GRAY**, and cite the deciding criterion (e.g. "AGENT — fails #3, requires judgment").

### C. Audit report
Print a table to the user:

| Section | Verdict | Reason | Proposed reflex_id (if candidate) |

Plus a one-line summary: "N candidate(s), M gray, the rest agent-layer."

### D. Per-candidate confirmation
For each REFLEX-CANDIDATE, ask the user **one at a time** before generating:
- Quote the section and the criteria it passed.
- Propose `reflex_id`, sketch `input_schema` / `output_schema`, list `examples`.
- Estimate invocation frequency. If <weekly, recommend skip.
- User says no → skip. User says yes → proceed to E.

GRAY items also need explicit confirmation, with the failing criterion called out.

### E. Generate (only approved candidates)

1. Render `reflex:` YAML from `templates/reflex_block.yaml.tmpl`. Fill every required field; omit unused optionals rather than write `null`.
2. Render `<reflex_id>.py` from `templates/reflex.py.tmpl` with `CONTRACT` populated and a `run(args)` stub that raises `NotImplementedError`. (Implementation is a follow-up; never silently fake it.)
3. **Patch the target SKILL.md frontmatter** — insert the `reflex:` block before the closing `---`. Do not touch the body. If frontmatter already has a `reflex:` block, **refuse and ask the user** — do not overwrite.
4. If you implemented `run()` (rather than leaving a stub), run `python3 <skill_dir>/<reflex_id>.py --selfcheck`. Report ok / fail. On fail, keep the file but warn the user that the implementation is broken.

## Hard constraints

- Never edit the body of the target SKILL.md — only its frontmatter.
- Never decide a boundary without per-candidate user confirmation.
- Never overwrite an existing `reflex:` block.
- Never auto-implement non-trivial `run()` logic — leave `NotImplementedError`
  and tell the user it's their job to fill in (you can offer a draft as a
  separate message, but never write it speculatively).

## Reflex contract reference (v1)

A SKILL.md frontmatter has either one `reflex:` block (single) or a
`reflexes:` list (multi). When multi, the hook validates input against each
entry's `input_schema` in order; first match wins. Use multi when a skill
exposes several deterministic sub-actions with disjoint schemas.

```yaml
reflex:
  reflex_id:        string         # required, kebab-case
  source_skill_id:  string         # required, must match the SKILL.md `name:`
  version:          "0.1.0"        # required, reflex semver
  contract_version: "1"            # required, schema-format version

  input_schema:  { ... }           # required, JSON Schema subset
  output_schema: { ... }           # required

  timeout_seconds: 10              # optional, default 10 — enforced via subprocess
  determinism: pure                # required: pure | external_api | impure
  on_failure: fallback_to_agent    # optional, default. Alt: hard_fail | retry_once
  side_effects: []                 # optional advisory list, e.g. ["writes /tmp"]

  examples:                        # required, >=1; drives --selfcheck
    - input:  { ... }
      output: { ... }

  negative_examples:               # required v0.2+, >=1; inputs that pass schema
                                   # but should be REJECTED (semantic misuse).
                                   # run() must raise. Drives second half of --selfcheck.
    - input:  { ... }              # e.g. {path: "/nonexistent"}, {from: "km", to: "年"}
```

Supported schema keywords (intentional subset): `type`, `properties`,
`required`, `enum`, `items`, `additionalProperties`, `minimum`, `maximum`,
`pattern`. Use anything else and the hook will pass the call through.

## Output discipline

When auditing: terse table, one-line verdict per section, no essay.
When generating: code first, three-line summary after. No design notes.
