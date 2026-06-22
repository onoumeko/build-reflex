#!/usr/bin/env python3
"""Static pre-filter for the 5-point reflex criteria.

Blueprint First paper (arxiv 2508.02721): the decision path itself should be
deterministic. Instead of asking the LLM to classify every section of a target
SKILL.md, apply heuristic rules first:

- CANDIDATE: looks reflexible (schema-like input/output, no judgment words)
- AGENT: clearly not (judgment verbs, free-text, skill chaining)
- GRAY: can't decide statically → LLM handles these

The LLM only sees GRAY items; CANDIDATE and AGENT go straight to the audit
table (per-candidate confirmation still required for candidates).

Criterion mapping:
  1. Deterministic input   → contains structured args (JSON / key=value / table rows)
  2. Deterministic output  → return value is a number/string/object, not prose
  3. No judgment           → no "judge"/"decide"/"interpret"/"weigh" verbs
  4. Enumerable failures   → mentions error/degradation handling
  5. No skill chaining     → no "invoke another skill"/"call the LLM" phrases

Usage: python3 reflex_audit.py <SKILL.md>  — prints JSON lines per section
"""
import json
import re
import sys
import yaml
from pathlib import Path

# Words that fail criterion #3 (no judgment)
JUDGMENT_WORDS = re.compile(
    r"\b(judge|decide|interpret|weigh|reason about|understand|consider|"
    r"evaluate|assess|think|feel|believe|infer|deduce|guess|estimate|"
    r"prioritize|negotiate|trade.?off)\b", re.IGNORECASE
)

# Words that fail criterion #5 (no skill chaining)
CHAINING_WORDS = re.compile(
    r"\b(call (another|the) skill|invoke (another|the) skill|call the LLM|"
    r"invoke the agent|use another reflex|trigger another|mid.?stream)\b",
    re.IGNORECASE
)

# Deterministic input patterns — positive signal for criterion #1
SCHEMA_LIKE = re.compile(
    r"(\{[^}]+\}|`[^`]+`|schemas?|JSON|input_schema|output_schema|"
    r"enum|key=?value|table|row|column|field|parameter|arg\b)",
    re.IGNORECASE
)

# Output patterns — positive signal for criterion #2
OUTPUT_VALUE = re.compile(
    r"\b(return|output|yield|produce|generate|result)\b.*\b(number|integer|"
    r"string|boolean|list|array|object|dict|JSON|structured|deterministic)\b",
    re.IGNORECASE
)


def split_sections(md_text):
    """Split markdown by ## headers. Returns list of (header, body)."""
    sections = []
    current_header = "(preamble)"
    current_body = []
    for line in md_text.split("\n"):
        if line.startswith("## "):
            if current_body:
                sections.append((current_header, "\n".join(current_body).strip()))
            current_header = line[3:].strip()
            current_body = []
        else:
            current_body.append(line)
    if current_body:
        sections.append((current_header, "\n".join(current_body).strip()))
    return sections


def classify_section(header, body):
    text = header + " " + body
    fails = []

    # Criterion 1: deterministic input
    if not SCHEMA_LIKE.search(text):
        fails.append("1-no_structured_args")

    # Criterion 2: deterministic output
    if not OUTPUT_VALUE.search(text) and not SCHEMA_LIKE.search(text):
        fails.append("2-output_not_a_value")

    # Criterion 3: no judgment
    if JUDGMENT_WORDS.search(text):
        fails.append("3-judgment_words")

    # Criterion 5: no skill chaining
    if CHAINING_WORDS.search(text):
        fails.append("5-chaining")

    # Criterion 4: enumerable failures — weakest signal, only flag if entirely absent
    mention_failures = re.search(r"\b(errors?|fail|missing|not found|timeout|invalid|bad)\b", text, re.IGNORECASE)
    if not mention_failures:
        fails.append("4-no_failure_mention")

    if not fails:
        return "REFLEX-CANDIDATE", ""
    if len(fails) >= 3:
        return "AGENT", ",".join(fails)
    return "GRAY", ",".join(fails)


def audit(path):
    fm_text = Path(path).read_text()
    # Split frontmatter and body
    if fm_text.startswith("---"):
        end = fm_text.find("\n---", 3)
        body = fm_text[end + 4:] if end >= 0 else fm_text
    else:
        body = fm_text
    sections = split_sections(body)
    results = []
    for header, body_text in sections:
        verdict, reason = classify_section(header, body_text)
        results.append({"section": header, "verdict": verdict, "reason": reason})
    return results


if __name__ == "__main__":
    if "--selfcheck" in sys.argv:
        # judgment word → AGENT or GRAY
        v, r = classify_section("Plan", "The agent should decide which approach to take based on context.")
        assert "3-judgment_words" in r, r
        # schema-like + value output → CANDIDATE
        v, r = classify_section("Count Lines", "Input: {path: string}. Output: {lines: integer, bytes: integer}. Errors: file not found.")
        assert v == "REFLEX-CANDIDATE", (v, r)
        # chaining → AGENT or GRAY
        v, r = classify_section("Orchestrate", "Call another skill to fetch data, then invoke the LLM mid-stream.")
        assert "5-chaining" in r, r
        print("ok")
        sys.exit(0)
    if len(sys.argv) < 2:
        print("usage: python3 reflex_audit.py <SKILL.md>", file=sys.stderr)
        sys.exit(2)
    path = sys.argv[1]
    for r in audit(path):
        print(json.dumps(r, ensure_ascii=False))