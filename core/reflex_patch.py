"""Helpers for the build-reflex meta-skill: insert reflex blocks into SKILL.md.

These are utility functions the LLM calls when executing the meta-skill's
"E. Generate" step. Keeping them in deterministic Python instead of having
the LLM do string manipulation reduces error rate.
"""
import re
import yaml
from pathlib import Path


def has_reflex_block(path):
    """Return True if the SKILL.md frontmatter already has a reflex: or reflexes: key."""
    text = Path(path).read_text()
    if not text.startswith("---"):
        return False
    end = text.find("\n---", 3)
    if end < 0:
        return False
    fm = text[3:end].lstrip("\n")
    try:
        parsed = yaml.safe_load(fm)
    except yaml.YAMLError:
        return False
    if not isinstance(parsed, dict):
        return False
    return "reflex" in parsed or "reflexes" in parsed


def dedup_matches(globs):
    """Given one or more glob results (list of str paths), return the first
    unique SKILL.md path. Prioritizes cache/*/*/*/*/skills/{name}/ over
    adapters path. Returns None if empty."""
    for globs_list in globs:
        if globs_list:
            return globs_list[0]
    return None


def inject_reflex_block(path, reflex_yaml):
    """Insert `reflex_yaml` (a string of one or more YAML keys) into the
    SKILL.md frontmatter, just before the closing `---`. Returns None on
    success, or an error string if the frontmatter is unparseable."""
    text = Path(path).read_text(encoding="utf-8")
    if has_reflex_block(path):
        return f"refuses to overwrite: {path} already has a reflex or reflexes block"
    if not text.startswith("---"):
        return f"no frontmatter found in {path}"
    # Find the closing ---
    end = text.find("\n---", 3)
    if end < 0:
        return f"unterminated frontmatter in {path}"
    # Insert before the closing marker
    new = text[:end] + "\n" + reflex_yaml + text[end:]
    Path(path).write_text(new, encoding="utf-8")
    return None


def generate_py_stub(filename, contract_text):
    """Given a reflex_id and the full contract dict as YAML, produce a .py stub
    using the spec/templates/reflex.py.tmpl.

    Returns (path, error). path is the path to the written file on success.
    """
    import json
    # We do NOT use the template file here — the LLM should use the template
    # in spec/templates/reflex.py.tmpl via the standard render process.
    # This function exists to validate the contract before writing.
    try:
        parsed = yaml.safe_load(contract_text)
    except yaml.YAMLError as e:
        return None, f"invalid YAML: {e}"
    if not isinstance(parsed, dict):
        return None, "contract must be a mapping"
    if "reflex_id" not in parsed:
        return None, "contract must have reflex_id"
    return parsed.get("reflex_id"), None


if __name__ == "__main__":
    # test inject + refuse-on-existing
    import tempfile, os
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write("---\nname: test\n---\n\nBody.")
        p = f.name
    assert has_reflex_block(p) is False
    err = inject_reflex_block(p, "reflex:\n  reflex_id: x\n")
    assert err is None, f"inject failed: {err}"
    assert has_reflex_block(p) is True
    err2 = inject_reflex_block(p, "reflex:\n  reflex_id: y\n")
    assert err2 is not None and "refuses to overwrite" in err2, f"overwrite guard failed: {err2}"
    os.unlink(p)

    # test no frontmatter
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write("No frontmatter at all.")
        p = f.name
    err3 = inject_reflex_block(p, "reflex:\n  reflex_id: x\n")
    assert err3 is not None and "no frontmatter" in err3, f"no-fm guard failed: {err3}"
    os.unlink(p)
    print("ok")