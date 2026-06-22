#!/usr/bin/env python3
"""Detect overlapping reflexes — when two input_schemas can both match the same args.

Required field sets are the heuristic: if two reflexes require the same set of
keys AND both accept those keys with the same types, they overlap. The hook
would silently pick the first one in the list, which is a bug.

Usage: python3 reflex_lint.py <path/to/SKILL.md>
"""
import json
import sys
import yaml
from pathlib import Path


def _required_set(reflex):
    s = reflex.get("input_schema") or {}
    return frozenset(s.get("required", []))


def _signature(reflex):
    """Return (required_set, {key: type}) for comparison."""
    s = reflex.get("input_schema") or {}
    req = frozenset(s.get("required", []))
    props = s.get("properties", {})
    types = frozenset((k, props[k].get("type")) for k in req if "type" in props.get(k, {}))
    return req, types


def check(reflexes):
    """Return list of (i, j, reflex_id_i, reflex_id_j) for overlapping pairs."""
    if not isinstance(reflexes, list):
        return []
    overlap = []
    for i in range(len(reflexes)):
        ri = reflexes[i]
        if not isinstance(ri, dict):
            continue
        req_i, types_i = _signature(ri)
        for j in range(i + 1, len(reflexes)):
            rj = reflexes[j]
            if not isinstance(rj, dict):
                continue
            req_j, types_j = _signature(rj)
            if req_i == req_j and types_i == types_j:
                overlap.append((i, j, ri.get("reflex_id"), rj.get("reflex_id")))
    return overlap


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    if not path or not path.exists():
        print("usage: python3 reflex_lint.py <SKILL.md>", file=sys.stderr)
        sys.exit(2)
    fm = yaml.safe_load("\n".join(path.read_text().split("---\n")[1:2]))
    candidates = []
    if isinstance(fm.get("reflex"), dict):
        candidates = [fm["reflex"]]
    if isinstance(fm.get("reflexes"), list):
        candidates = fm["reflexes"]
    overlaps = check(candidates)
    if overlaps:
        for i, j, id1, id2 in overlaps:
            print(f"OVERLAP: reflexes[{i}]={id1} and [{j}]={id2} have identical required field sets. "
                  f"Add a required discriminator field to one of them.", file=sys.stderr)
        sys.exit(1)
    print("no overlaps")
    sys.exit(0)


if __name__ == "__main__":
    main()