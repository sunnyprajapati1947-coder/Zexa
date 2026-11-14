---
name: csv-processor
description: Parses, transforms, validates, and exports CSV files. Use when reading, cleaning, filtering, merging, or converting CSV data.
license: Apache-2.0
compatibility: Claude Code, Codex, Gemini CLI
metadata:
  author: ai-skills
  version: "1.0"
  category: data-analytics
  tags: csv, pandas, python-csv, data-processing, encoding, chunking
---

## Overview

Handles real-world CSV processing tasks reliably: encoding detection, delimiter sniffing, header normalization, row filtering and column selection, merging multiple CSVs, chunked processing for large files, validation against schemas, and export to CSV, JSON, Parquet, or Excel with proper quoting and escaping.

## When to Use This Skill

- Ingesting or cleaning data delivered as CSV exports.
- Combining data from multiple CSV sources.
- Converting CSV to other formats for downstream systems.
- The user provides CSV files or describes CSV processing needs.

## Prerequisites

- Python with `pandas` (recommended for most work) or standard `csv` module for very simple cases.
- The CSV file(s) or a description of their structure.
- For large files: enough memory or a chunked strategy.

## Steps

1. **Inspect the CSV**:
   - Open with a text editor or `head -c 1000`.
   - Determine encoding (use `chardet` or `charset_normalizer`).
   - Sniff delimiter (`,` , `;`, `\t`).

2. **Read safely**:
   - `pd.read_csv(..., encoding=..., sep=..., engine='c' or 'python')`.
   - `dtype=str` initially to avoid type inference surprises, then cast.
   - `on_bad_lines='skip'` or custom error handler for malformed rows.

3. **Header & column normalization**:
   - Lowercase, strip, replace spaces with underscores.
   - Handle duplicate column names.
   - Rename using a mapping if the source headers are bad.

4. **Filtering & selection**:
   - Boolean indexing for rows.
   - Column list or regex for selection.
   - Drop or keep based on business rules.

5. **Merging multiple CSVs**:
   - `pd.concat` with `ignore_index=True`.
   - Or `pd.merge` on keys for relational join.
   - Handle schema differences between files.

6. **Chunked processing** (for >1GB or memory-constrained):
   - `pd.read_csv(..., chunksize=100_000)`.
   - Process each chunk, write to Parquet or append to output.
   - Aggregate as you go when possible.

7. **Validation**:
   - Required columns present.
   - No unexpected nulls in key fields.
   - Value ranges or allowed sets.
   - Row count within expected bounds.

8. **Export**:
   - `to_csv(index=False, quoting=csv.QUOTE_MINIMAL)`.
   - Prefer Parquet for large/intermediate data (much faster, smaller, typed).
   - Excel with `openpyxl` for business users (with formatting).

9. **Output**:
   - Reusable `process_csv(input_path, output_path)` function or notebook cells.
   - Handling for common real-world messiness (quotes, newlines in fields, BOM).

## Examples

A robust script that reads a messy sales CSV (mixed encodings, bad headers, embedded newlines), cleans it, merges with a second "customers" CSV, validates, and exports to Parquet + a summary Excel report is included.

## Edge Cases & Error Handling

- **Embedded delimiters or quotes**: Use the `csv` module's dialect or pandas with proper quoting.
- **Huge files on low memory**: Always offer the chunked path.
- **Date formats**: Multiple formats in one column — use `dateutil.parser` or `pd.to_datetime` with `format` inference.

## Verification

1. The script runs without crashing on the provided (messy) file.
2. Output file has the expected columns, dtypes, and row count.
3. Manual spot checks in the output match expectations.
4. Re-running on the same input produces bit-identical output (when deterministic).
5. Success: The CSV is turned into clean, usable data with a clear audit trail of transformations.

## References

- [pandas.read_csv](https://pandas.pydata.org/docs/reference/api/pandas.read_csv.html)
- [Python csv module](https://docs.python.org/3/library/csv.html)
- [chardet](https://github.com/chardet/chardet)
- [Parquet vs CSV](https://databricks.com/blog/2018/08/16/how-to-use-parquet-files-in-spark-sql.html)
