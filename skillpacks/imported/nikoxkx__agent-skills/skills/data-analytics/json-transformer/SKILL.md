---
name: json-transformer
description: Transforms, reshapes, and validates JSON data structures. Use when normalizing API responses, converting nested JSON to flat tables, or validating JSON against a schema.
license: Apache-2.0
compatibility: Claude Code, Codex, Gemini CLI
metadata:
  author: ai-skills
  version: "1.0"
  category: data-analytics
  tags: json, jq, json-schema, pandas, normalization, validation
---

## Overview

Transforms and validates JSON data using jq (CLI), Python (`json`, `jsonpath-ng`, `pandas.json_normalize`), and JSON Schema (`jsonschema` library). Covers common patterns: flattening nested objects/arrays, extracting specific fields, array of objects → table, schema validation, streaming large JSON files, and producing clean output for databases or downstream processing.

## When to Use This Skill

- Normalizing complex API responses (nested, inconsistent).
- Converting JSON logs or documents into tabular form for analysis.
- Validating incoming JSON payloads against a contract.
- The user provides JSON files or describes JSON transformation needs.

## Prerequisites

- `jq` installed for CLI transformations (highly recommended).
- Python with `pandas`, `jsonschema`, `jsonpath-ng` (optional but powerful).
- The JSON data (file, API response, or stdin).

## Steps

1. **Inspect the JSON**:
   - `jq '.' file.json | head -100` or Python `json.load`.
   - Identify the shape (object, array of objects, deeply nested).

2. **Choose tool by use case**:
   - Simple reshaping / extraction: `jq`.
   - To pandas DataFrame: `pandas.json_normalize`.
   - Validation: JSON Schema + `jsonschema`.
   - Streaming large files: `ijson` (Python) or `jq` with `--stream`.

3. **Common jq patterns** (provide ready-to-use one-liners):
   - Extract array: `.items[]`
   - Flatten nested: `.user | {id, name, "address.city": .address.city}`
   - Filter + map.
   - Group by.

4. **pandas.json_normalize**:
   - `pd.json_normalize(data, record_path=['results'], meta=['query'])`.
   - `errors='ignore'` for inconsistent structures.

5. **JSON Schema validation**:
   - Write a schema (draft 2020-12 or 2019-09).
   - Validate in Python or with `ajv` (JS) / `check-jsonschema` (CLI).
   - Produce clear error messages with path to the bad field.

6. **Streaming large JSON**:
   - For NDJSON (newline-delimited): process line by line.
   - For large arrays: use `ijson.items(f, 'item')`.

7. **Output**:
   - `jq` one-liners or script.
   - Python function `transform_json(input_path) -> pd.DataFrame or list[dict]`.
   - JSON Schema file.
   - Example of before/after shape.

## Examples

- Normalize a complex GitHub API search response (nested user + repo objects) into a flat table using both `jq` and `pandas.json_normalize`.
- Validate incoming webhook payloads against a strict schema and quarantine bad ones.
- Stream-process a 500MB NDJSON log file and extract only error events.

## Edge Cases & Error Handling

- **Inconsistent nesting**: Use `errors='ignore'` or `try/except` per record + dead letter.
- **Huge files**: Never load the entire thing into memory.
- **Unicode / escaping issues**: Ensure UTF-8 throughout.

## Verification

1. Run the transformation on sample input — output shape matches expectation.
2. Validate a good and a deliberately bad JSON — errors are clear and point to the bad field.
3. For large files: memory usage stays reasonable (monitor with `htop` or similar).
4. Re-run produces deterministic output.
5. Success: JSON is turned into the exact shape needed for the next step, with validation protecting downstream systems.

## References

- [jq Manual](https://jqlang.github.io/jq/manual/)
- [pandas.json_normalize](https://pandas.pydata.org/docs/reference/api/pandas.json_normalize.html)
- [JSON Schema](https://json-schema.org/)
- [ijson](https://github.com/ICRAR/ijson)
- [jsonpath-ng](https://github.com/h2non/jsonpath-ng)
