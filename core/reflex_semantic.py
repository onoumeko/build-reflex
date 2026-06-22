"""Semantic preconditions — checks the hook runs AFTER schema validation,
BEFORE invoking the script.

Why: JSON Schema catches interface misuse (wrong type, missing required) but
not semantic misuse (per arxiv 2603.13404). A schema-valid {path: "/nonexistent"}
should not reach count-lines.py — it'll just raise OSError and look like a
script bug. Better: refuse upfront with a clean fallback_to_agent reminder.

A precondition is `{check: "<name>", arg: "<arg key>"}`. `check` names a function
in CHECKS; `arg` names the key in args whose value gets passed. Returns
(ok: bool, reason: str).

To extend: add a function to CHECKS. Keep them stdlib-only and fast (<10ms).
"""
import os
import re
from datetime import datetime


def _file_exists(v):
    if not isinstance(v, str): return False, "not a string path"
    return (os.path.isfile(v), f"file not found: {v}") if not os.path.isfile(v) else (True, "")


def _file_is_text(v):
    if not isinstance(v, str): return False, "not a string path"
    if not os.path.isfile(v): return False, f"file not found: {v}"
    try:
        with open(v, "rb") as f:
            chunk = f.read(8192)
        if b"\x00" in chunk:
            return False, f"file looks binary (NUL byte in first 8KB): {v}"
        return True, ""
    except OSError as e:
        return False, str(e)


def _non_empty_string(v):
    return (isinstance(v, str) and len(v.strip()) > 0,
            "empty or non-string")


def _valid_regex(v):
    if not isinstance(v, str): return False, "not a string"
    try:
        re.compile(v)
        return True, ""
    except re.error as e:
        return False, f"invalid regex: {e}"


def _valid_iso_date(v):
    if not isinstance(v, str): return False, "not a string"
    try:
        datetime.fromisoformat(v)
        return True, ""
    except ValueError as e:
        return False, f"not ISO 8601: {e}"


def _is_unit_length(v):
    units = {"mm","cm","m","km","in","ft","yd","mi"}
    return (isinstance(v, str) and v.lower() in units,
            f"not a known length unit: {v}")


def _is_unit_mass(v):
    units = {"mg","g","kg","t","oz","lb"}
    return (isinstance(v, str) and v.lower() in units,
            f"not a known mass unit: {v}")


def _is_unit_temp(v):
    return (isinstance(v, str) and v.lower() in ("c","f","k"),
            f"not a temperature unit: {v}")


def _is_unit_any(v):
    for fn in (_is_unit_length, _is_unit_mass, _is_unit_temp):
        ok, _ = fn(v)
        if ok: return True, ""
    return False, f"not a known unit: {v}"


CHECKS = {
    "file_exists":     _file_exists,
    "file_is_text":    _file_is_text,
    "non_empty":       _non_empty_string,
    "valid_regex":     _valid_regex,
    "valid_iso_date":  _valid_iso_date,
    "is_unit_length":  _is_unit_length,
    "is_unit_mass":    _is_unit_mass,
    "is_unit_temp":    _is_unit_temp,
    "is_unit_any":     _is_unit_any,
}


def evaluate(preconditions, args):
    """Run all preconditions against args. Return None if all pass, else error string."""
    if not preconditions:
        return None
    for i, pc in enumerate(preconditions):
        if not isinstance(pc, dict):
            continue
        check_name = pc.get("check")
        arg_key    = pc.get("arg")
        if not check_name or not arg_key:
            continue
        fn = CHECKS.get(check_name)
        if fn is None:
            return f"precondition[{i}]: unknown check {check_name!r}"
        if arg_key not in args:
            return f"precondition[{i}]: arg {arg_key!r} not in input"
        ok, reason = fn(args[arg_key])
        if not ok:
            return f"precondition[{i}] {check_name}({arg_key}={args[arg_key]!r}) failed: {reason}"
    return None


if __name__ == "__main__":
    # tests
    assert evaluate(None, {}) is None
    assert evaluate([], {}) is None
    # file_exists
    assert evaluate([{"check":"file_exists","arg":"p"}], {"p":"/etc/hostname"}) is None
    err = evaluate([{"check":"file_exists","arg":"p"}], {"p":"/nope/xyz"})
    assert err and "not found" in err, err
    # unknown check name
    err = evaluate([{"check":"nonsense","arg":"x"}], {"x":1})
    assert err and "unknown check" in err, err
    # missing arg key
    err = evaluate([{"check":"file_exists","arg":"missing"}], {"x":1})
    assert err and "not in input" in err, err
    # unit_any
    assert evaluate([{"check":"is_unit_any","arg":"u"}], {"u":"km"}) is None
    err = evaluate([{"check":"is_unit_any","arg":"u"}], {"u":"年"})
    assert err and "not a known unit" in err, err
    # regex
    assert evaluate([{"check":"valid_regex","arg":"p"}], {"p":r"\d+"}) is None
    err = evaluate([{"check":"valid_regex","arg":"p"}], {"p":"[invalid"})
    assert err and "invalid regex" in err
    # iso date
    assert evaluate([{"check":"valid_iso_date","arg":"d"}], {"d":"2026-06-22"}) is None
    err = evaluate([{"check":"valid_iso_date","arg":"d"}], {"d":"hello"})
    assert err and "not ISO 8601" in err
    print("ok")
