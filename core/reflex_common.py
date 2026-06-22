"""Minimal JSON Schema subset validator for reflex contracts.

Supports: type, properties, required, enum, items, additionalProperties,
minimum, maximum, pattern. Intentionally narrow — reflex schemas are simple.
Stdlib only.
"""
import re

_TYPES = {
    "string":  str,
    "integer": int,
    "number":  (int, float),
    "boolean": bool,
    "object":  dict,
    "array":   list,
    "null":    type(None),
}


class ValidationError(ValueError):
    pass


def validate(obj, schema, path="$"):
    """Raise ValidationError if obj does not match schema. Return None on pass."""
    if not isinstance(schema, dict):
        return  # untyped — accept anything
    t = schema.get("type")
    if t:
        py = _TYPES.get(t)
        if py is None:
            raise ValidationError(f"{path}: unknown type {t!r} in schema")
        # bool is subclass of int in Python — guard
        if t == "integer" and isinstance(obj, bool):
            raise ValidationError(f"{path}: expected integer, got boolean")
        if not isinstance(obj, py):
            raise ValidationError(f"{path}: expected {t}, got {type(obj).__name__}")
    if "enum" in schema and obj not in schema["enum"]:
        raise ValidationError(f"{path}: {obj!r} not in enum {schema['enum']}")
    if isinstance(obj, (int, float)) and not isinstance(obj, bool):
        if "minimum" in schema and obj < schema["minimum"]:
            raise ValidationError(f"{path}: {obj} < minimum {schema['minimum']}")
        if "maximum" in schema and obj > schema["maximum"]:
            raise ValidationError(f"{path}: {obj} > maximum {schema['maximum']}")
    if isinstance(obj, str) and "pattern" in schema:
        if not re.search(schema["pattern"], obj):
            raise ValidationError(f"{path}: {obj!r} does not match pattern {schema['pattern']!r}")
    if isinstance(obj, dict):
        props = schema.get("properties", {})
        for req in schema.get("required", []):
            if req not in obj:
                raise ValidationError(f"{path}: missing required property {req!r}")
        for k, v in obj.items():
            if k in props:
                validate(v, props[k], f"{path}.{k}")
            elif schema.get("additionalProperties") is False:
                raise ValidationError(f"{path}: unexpected property {k!r}")
    if isinstance(obj, list) and "items" in schema:
        for i, item in enumerate(obj):
            validate(item, schema["items"], f"{path}[{i}]")


def is_valid(obj, schema):
    try:
        validate(obj, schema)
        return True
    except ValidationError:
        return False


if __name__ == "__main__":
    # one runnable check.
    s = {"type": "object",
         "properties": {"path": {"type": "string"}, "n": {"type": "integer", "minimum": 0}},
         "required": ["path"], "additionalProperties": False}
    assert is_valid({"path": "/etc/hosts"}, s)
    assert is_valid({"path": "/etc/hosts", "n": 3}, s)
    assert not is_valid({"path": 1}, s)              # wrong type
    assert not is_valid({}, s)                        # missing required
    assert not is_valid({"path": "x", "z": 1}, s)    # additionalProperties: false
    assert not is_valid({"path": "x", "n": -1}, s)   # minimum
    assert not is_valid({"path": "x", "n": True}, s) # bool != integer
    assert is_valid("ok", {"enum": ["ok", "error"]})
    assert not is_valid("nope", {"enum": ["ok", "error"]})
    print("ok")
