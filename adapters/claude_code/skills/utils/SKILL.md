---
name: utils
displayName: utils (starter reflex pack)
description: >
  Deterministic helpers (LLM never runs these; the hook routes by input_schema
  and returns script output directly). Available reflexes:
  file-hash {path, algo} → {hash, algo, bytes};
  count-lines {path} → {lines, bytes};
  b64-encode {text} → {b64};
  b64-decode {b64} → {text};
  json-path {json, path} → {value};
  regex-extract {text, pattern, group?} → {matches};
  date-add {date, days?, hours?, minutes?} → {date};
  unit-convert {value, from, to} → {value, from, to}.
  Triggers: hash/count lines/base64/json-path/regex/date-add/convert.
license: MIT
reflex_index:
  - "file-hash {path, algo} → {hash, algo, bytes}"
  - "count-lines {path} → {lines, bytes}"
  - "b64-encode {text} → {b64}"
  - "b64-decode {b64} → {text}"
  - "json-path {json, path} → {value}"
  - "regex-extract {text, pattern, group?} → {matches}"
  - "date-add {date, days?, hours?, minutes?} → {date}"
  - "unit-convert {value, from, to} → {value, from, to}"
reflexes:
  - reflex_id: file-hash
    source_skill_id: utils
    version: "0.1.0"
    contract_version: "1"
    input_schema:
      type: object
      properties:
        path: { type: string }
        algo: { type: string, enum: ["sha256", "sha1", "md5"] }
      required: [path, algo]
      additionalProperties: false
    output_schema:
      type: object
      properties:
        hash:  { type: string }
        algo:  { type: string }
        bytes: { type: integer }
      required: [hash, algo, bytes]
      additionalProperties: false
    timeout_seconds: 30
    determinism: pure
    on_failure: fallback_to_agent
    examples:
      - input:  { path: "/etc/hostname", algo: "sha256" }
        output: { hash: "*", algo: "sha256", bytes: 0 }   # selfcheck stubbed below
    negative_examples:
      - input: { path: "/definitely/does/not/exist/xyz", algo: "sha256" }
      - input: { path: "/etc/hostname", algo: "crc32" }   # algo not in enum bypassed in this list; semantic check inside run()

  - reflex_id: count-lines
    source_skill_id: utils
    version: "0.1.0"
    contract_version: "1"
    input_schema:
      type: object
      properties:
        path: { type: string }
      required: [path]
      additionalProperties: false
    output_schema:
      type: object
      properties:
        lines: { type: integer }
        bytes: { type: integer }
      required: [lines, bytes]
      additionalProperties: false
    timeout_seconds: 10
    determinism: pure
    on_failure: fallback_to_agent
    examples:
      - input:  { path: "/etc/hostname" }
        output: { lines: 0, bytes: 0 }
    negative_examples:
      - input: { path: "/definitely/does/not/exist/xyz" }

  - reflex_id: b64-encode
    source_skill_id: utils
    version: "0.1.0"
    contract_version: "1"
    input_schema:
      type: object
      properties:
        text: { type: string }
      required: [text]
      additionalProperties: false
    output_schema:
      type: object
      properties:
        b64: { type: string }
      required: [b64]
      additionalProperties: false
    timeout_seconds: 5
    determinism: pure
    on_failure: fallback_to_agent
    examples:
      - input:  { text: "hello" }
        output: { b64: "aGVsbG8=" }

  - reflex_id: b64-decode
    source_skill_id: utils
    version: "0.1.0"
    contract_version: "1"
    input_schema:
      type: object
      properties:
        b64: { type: string }
      required: [b64]
      additionalProperties: false
    output_schema:
      type: object
      properties:
        text: { type: string }
      required: [text]
      additionalProperties: false
    timeout_seconds: 5
    determinism: pure
    on_failure: fallback_to_agent
    examples:
      - input:  { b64: "aGVsbG8=" }
        output: { text: "hello" }
    negative_examples:
      - input: { b64: "this is not valid base64 !!!" }

  - reflex_id: json-path
    source_skill_id: utils
    version: "0.1.0"
    contract_version: "1"
    input_schema:
      type: object
      properties:
        json: { type: string }
        path: { type: string }
      required: [json, path]
      additionalProperties: false
    output_schema:
      type: object
      properties:
        value: {}
      required: [value]
      additionalProperties: false
    timeout_seconds: 5
    determinism: pure
    on_failure: fallback_to_agent
    examples:
      - input:  { json: '{"a":{"b":[10,20]}}', path: "a.b[1]" }
        output: { value: 20 }
    negative_examples:
      - input: { json: "not json at all", path: "a.b" }
      - input: { json: '{"a":1}', path: "missing.key" }

  - reflex_id: regex-extract
    source_skill_id: utils
    version: "0.1.0"
    contract_version: "1"
    input_schema:
      type: object
      properties:
        text:    { type: string }
        pattern: { type: string }
        group:   { type: integer, minimum: 0 }
      required: [text, pattern]
      additionalProperties: false
    output_schema:
      type: object
      properties:
        matches:
          type: array
          items: { type: string }
      required: [matches]
      additionalProperties: false
    timeout_seconds: 5
    determinism: pure
    on_failure: fallback_to_agent
    examples:
      - input:  { text: "a1 b22 c333", pattern: "\\d+" }
        output: { matches: ["1", "22", "333"] }
    negative_examples:
      - input: { text: "x", pattern: "[invalid" }

  - reflex_id: date-add
    source_skill_id: utils
    version: "0.1.0"
    contract_version: "1"
    input_schema:
      type: object
      properties:
        date:    { type: string }
        days:    { type: integer }
        hours:   { type: integer }
        minutes: { type: integer }
      required: [date]
      additionalProperties: false
    output_schema:
      type: object
      properties:
        date: { type: string }
      required: [date]
      additionalProperties: false
    timeout_seconds: 5
    determinism: pure
    on_failure: fallback_to_agent
    examples:
      - input:  { date: "2026-01-01", days: 30 }
        output: { date: "2026-01-31" }
    negative_examples:
      - input: { date: "not a date", days: 1 }

  - reflex_id: unit-convert
    source_skill_id: utils
    version: "0.1.0"
    contract_version: "1"
    input_schema:
      type: object
      properties:
        value: { type: number }
        from:  { type: string }
        to:    { type: string }
      required: [value, from, to]
      additionalProperties: false
    output_schema:
      type: object
      properties:
        value: { type: number }
        from:  { type: string }
        to:    { type: string }
      required: [value, from, to]
      additionalProperties: false
    timeout_seconds: 5
    determinism: pure
    on_failure: fallback_to_agent
    examples:
      - input:  { value: 1, from: "km", to: "m" }
        output: { value: 1000, from: "km", to: "m" }
    negative_examples:
      - input: { value: 1, from: "km", to: "年" }       # unknown unit
      - input: { value: 1, from: "km", to: "kg" }        # mixed dimension
---

# utils

A starter pack of pure, deterministic reflexes. Each is routed by matching
its `input_schema`. Every reflex here is `determinism: pure`, so results are
cached on disk.

## Available reflexes

| reflex_id      | input                                             | output                          |
|----------------|---------------------------------------------------|---------------------------------|
| file-hash      | `{path, algo?}`                                   | `{hash, algo, bytes}`           |
| count-lines    | `{path}`                                          | `{lines, bytes}`                |
| b64-encode     | `{text}`                                          | `{b64}`                         |
| b64-decode     | `{b64}`                                           | `{text}`                        |
| json-path      | `{json, path}` — dotted: `a.b[0].c`               | `{value}`                       |
| regex-extract  | `{text, pattern, group?}`                         | `{matches: [string]}`           |
| date-add       | `{date, days?, hours?, minutes?}` — ISO 8601      | `{date}` (ISO 8601)             |
| unit-convert   | `{value, from, to}` — length/mass/temperature     | `{value, from, to}`             |

Add more by editing the `reflexes:` list in this file's frontmatter and
dropping a sibling `<reflex_id>.py`.
