#!/usr/bin/env python3
"""Reflex: unit-convert. Length / mass / temperature."""
import json, sys

CONTRACT = {
    "reflex_id": "unit-convert",
    "input_schema": {"type": "object",
                     "properties": {"value": {"type": "number"},
                                    "from": {"type": "string"}, "to": {"type": "string"}},
                     "required": ["value", "from", "to"], "additionalProperties": False},
    "output_schema": {"type": "object",
                      "properties": {"value": {"type": "number"},
                                     "from": {"type": "string"}, "to": {"type": "string"}},
                      "required": ["value", "from", "to"], "additionalProperties": False},
    "version": "0.1.0",
}

# meters / grams reference units
_LENGTH = {"mm": 0.001, "cm": 0.01, "m": 1, "km": 1000,
           "in": 0.0254, "ft": 0.3048, "yd": 0.9144, "mi": 1609.344}
_MASS   = {"mg": 0.001, "g": 1, "kg": 1000, "t": 1e6,
           "oz": 28.3495, "lb": 453.592}

def _to_kelvin(v, u):
    return {"k": v, "c": v + 273.15, "f": (v - 32) * 5 / 9 + 273.15}[u]
def _from_kelvin(v, u):
    return {"k": v, "c": v - 273.15, "f": (v - 273.15) * 9 / 5 + 32}[u]

def run(args):
    v, f, t = args["value"], args["from"], args["to"]
    fl, tl = f.lower(), t.lower()
    if fl in _LENGTH and tl in _LENGTH:
        out = v * _LENGTH[fl] / _LENGTH[tl]
    elif fl in _MASS and tl in _MASS:
        out = v * _MASS[fl] / _MASS[tl]
    elif fl in ("c", "f", "k") and tl in ("c", "f", "k"):
        out = _from_kelvin(_to_kelvin(v, fl), tl)
    else:
        raise ValueError(f"unsupported conversion: {f} -> {t}")
    return {"value": out, "from": f, "to": t}

if __name__ == "__main__":
    if "--selfcheck" in sys.argv:
        assert run({"value": 1, "from": "km", "to": "m"})["value"] == 1000
        assert abs(run({"value": 100, "from": "C", "to": "F"})["value"] - 212) < 1e-9
        assert abs(run({"value": 1, "from": "kg", "to": "lb"})["value"] - 2.20462262) < 1e-4
        print("ok")
    else:
        try: json.dump(run(json.loads(sys.stdin.read() or "{}")), sys.stdout)
        except Exception as e: print(f"err: {e}", file=sys.stderr); sys.exit(1)
