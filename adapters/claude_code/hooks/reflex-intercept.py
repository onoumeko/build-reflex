#!/usr/bin/env python3
"""PreToolUse hook: intercept Skill calls and run their reflex(es) when present.

Hook protocol:
  stdin  : {"tool_name": "...", "tool_input": {...}, ...}
  stdout : either {} (let through) or
           {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                   "permissionDecision": "deny",
                                   "permissionDecisionReason": "<body>"}}
  exit   : 0 always

Supports:
  - Single reflex (`reflex:` block) or multi-reflex (`reflexes:` list) per SKILL.md.
    Multi: each candidate validated in order; first input_schema match wins.
  - Contract drift check between SKILL.md and script CONTRACT — refuses to run
    on mismatch (logged, falls through to agent).
  - On-disk LRU cache for determinism: pure reflexes.
  - Fallback path injects a <system-reminder> into the tool result so the LLM
    knows a reflex was attempted and why it failed.
  - One-line JSON log per call to /tmp/reflex-intercept.log for stats.
"""
import json
import os
import subprocess
import sys
import time
from glob import glob
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "core"))
import reflex_common  # noqa: E402
import reflex_cache   # noqa: E402
import reflex_drift   # noqa: E402

try:
    import yaml
except ImportError:
    print("{}")
    sys.exit(0)

LOG = "/tmp/reflex-intercept.log"
MAX_LOG_BYTES = 5 * 1024 * 1024  # 5 MB
SKILL_GLOBS = [
    "/root/.claude/plugins/cache/*/*/*/skills/{skill}/SKILL.md",
    "/root/.claude/plugins/cache/*/*/*/adapters/claude_code/skills/{skill}/SKILL.md",
]


def _rotate_log():
    try:
        st = os.stat(LOG)
        if st.st_size > MAX_LOG_BYTES:
            os.rename(LOG, LOG + ".1")
    except OSError:
        pass


def let_through(reminder=None):
    if reminder:
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "additionalContext": reminder,
            }
        }))
    else:
        print("{}")
    sys.exit(0)


def intercept(body):
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": body,
        }
    }))
    sys.exit(0)


def log(event):
    event["t"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    _rotate_log()
    try:
        with open(LOG, "a") as f:
            f.write(json.dumps(event, separators=(",", ":")) + "\n")
    except OSError:
        pass


def parse_frontmatter(path):
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end < 0:
        return None
    try:
        return yaml.safe_load(text[3:end].lstrip("\n"))
    except yaml.YAMLError:
        return None


def normalize_args(raw):
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        s = raw.strip()
        if not s:
            return {}
        try:
            parsed = json.loads(s)
            return parsed if isinstance(parsed, dict) else {"_raw": raw}
        except json.JSONDecodeError:
            return {"_raw": raw}
    return {"_raw": raw}


def pick_reflex(fm, args):
    """Return (reflex, last_schema_err). Tries single-reflex block first, then
    list. First input_schema match wins."""
    if isinstance(fm.get("reflex"), dict):
        candidates = [fm["reflex"]]
    elif isinstance(fm.get("reflexes"), list):
        candidates = [r for r in fm["reflexes"] if isinstance(r, dict)]
    else:
        return None, None
    last = None
    for r in candidates:
        try:
            reflex_common.validate(args, r.get("input_schema") or {})
            return r, None
        except reflex_common.ValidationError as e:
            last = str(e)
    return None, last


def run_reflex(script, args, timeout):
    t0 = time.time()
    try:
        proc = subprocess.run(
            ["python3", str(script)],
            input=json.dumps(args),
            capture_output=True, text=True, timeout=timeout,
        )
        return proc.returncode, proc.stdout, proc.stderr, int((time.time() - t0) * 1000)
    except subprocess.TimeoutExpired:
        return 124, "", f"timeout after {timeout}s", int((time.time() - t0) * 1000)


def estimate_tokens(text):
    # ~4 chars per token. Good enough for stats.
    return max(1, len(text) // 4)


def main():
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        let_through()

    if payload.get("tool_name") != "Skill":
        let_through()

    tool_input = payload.get("tool_input") or {}
    skill = tool_input.get("skill") or tool_input.get("skill_name")
    if not skill:
        let_through()
    args = normalize_args(tool_input.get("args"))

    # 1. Locate SKILL.md (try both old-skills and adapters paths)
    matches = []
    for g in SKILL_GLOBS:
        matches = glob(g.format(skill=skill))
        if matches:
            break
    if not matches:
        let_through()
    skill_md = Path(matches[0])

    # 2. Parse frontmatter, find a reflex
    fm = parse_frontmatter(skill_md)
    if not isinstance(fm, dict):
        let_through()
    reflex, schema_err = pick_reflex(fm, args)
    if reflex is None:
        if schema_err:
            log({"skill": skill, "status": "schema_miss", "err": schema_err[:200]})
        let_through()

    reflex_id = reflex.get("reflex_id")
    if not reflex_id:
        let_through()
    script = skill_md.parent / f"{reflex_id}.py"
    if not script.exists():
        log({"skill": skill, "reflex_id": reflex_id, "status": "script_missing"})
        let_through()

    # 3. Drift check
    drift = reflex_drift.check_drift(reflex, script)
    if drift:
        log({"skill": skill, "reflex_id": reflex_id, "status": "drift", "err": drift})
        let_through(reminder=f"reflex {reflex_id} not invoked: {drift}. Regenerate via build-reflex.")

    timeout = int(reflex.get("timeout_seconds") or 10)
    on_failure = reflex.get("on_failure") or "fallback_to_agent"
    determinism = reflex.get("determinism") or "pure"

    # 4. Cache lookup for pure reflexes
    if determinism == "pure":
        cached = reflex_cache.get(reflex_id, args)
        if cached is not None:
            log({"skill": skill, "reflex_id": reflex_id, "status": "cache_hit",
                 "dur_ms": 0, "saved_tokens": estimate_tokens(cached)})
            intercept(cached)

    # 5. Run (with retry_once support)
    code, out, err, dur = run_reflex(script, args, timeout)
    if code != 0 and on_failure == "retry_once":
        log({"skill": skill, "reflex_id": reflex_id, "status": "retry_after_exit",
             "exit": code, "dur_ms": dur})
        code, out, err, dur = run_reflex(script, args, timeout)

    # 6. Success path
    if code == 0:
        try:
            parsed = json.loads(out)
            reflex_common.validate(parsed, reflex.get("output_schema") or {})
            if determinism == "pure":
                reflex_cache.put(reflex_id, args, out.strip())
            log({"skill": skill, "reflex_id": reflex_id, "status": "ok",
                 "dur_ms": dur, "saved_tokens": estimate_tokens(out)})
            intercept(out.strip())
        except (json.JSONDecodeError, reflex_common.ValidationError) as e:
            code = 2
            err = f"output validation failed: {e}\n{err}"

    # 7. Failure path
    log({"skill": skill, "reflex_id": reflex_id, "status": "fail",
         "exit": code, "dur_ms": dur, "err": err[:200].replace("\n", " ")})
    msg = f"reflex {reflex_id} failed (exit {code}). Reason: {err[:150].strip()}"
    if on_failure == "hard_fail":
        intercept(msg)
    let_through(reminder=msg + " — falling back to LLM handling.")


if __name__ == "__main__":
    main()
