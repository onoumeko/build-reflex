"""Detect drift between SKILL.md `reflex:` block and the sibling .py CONTRACT.

The hook calls `check_drift(reflex_block, script_path)` and refuses to run on
mismatch. Surfaces "regenerate or fix CONTRACT" instead of running stale args.
"""
import ast
import hashlib
import json


def hash_contract(d):
    """Stable hash of the parts of the contract that affect script behavior."""
    keep = {k: d.get(k) for k in ("reflex_id", "input_schema", "output_schema", "version")}
    return hashlib.sha256(
        json.dumps(keep, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()[:16]


def extract_script_contract(script_path):
    """Parse the .py file's top-level CONTRACT = {...} literal. Returns dict or None."""
    try:
        tree = ast.parse(open(script_path).read())
    except (OSError, SyntaxError):
        return None
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            t = node.targets[0]
            if isinstance(t, ast.Name) and t.id == "CONTRACT":
                try:
                    return ast.literal_eval(node.value)
                except (ValueError, SyntaxError):
                    return None
    return None


def check_drift(reflex_block, script_path):
    """Return None if in sync, else a string explaining the mismatch."""
    script_contract = extract_script_contract(script_path)
    if script_contract is None:
        return None  # no CONTRACT in script — can't compare, allow
    a, b = hash_contract(reflex_block), hash_contract(script_contract)
    if a != b:
        return f"contract drift: SKILL.md={a} script={b}"
    return None


if __name__ == "__main__":
    # one runnable check
    a = {"reflex_id": "x", "input_schema": {"type": "object"}, "output_schema": {}, "version": "1"}
    b = {"reflex_id": "x", "input_schema": {"type": "object"}, "output_schema": {}, "version": "1"}
    c = {"reflex_id": "x", "input_schema": {"type": "array"},  "output_schema": {}, "version": "1"}
    assert hash_contract(a) == hash_contract(b)
    assert hash_contract(a) != hash_contract(c)
    print("ok")
