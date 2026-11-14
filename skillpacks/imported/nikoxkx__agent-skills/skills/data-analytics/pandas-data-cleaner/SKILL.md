---
name: pandas-data-cleaner
description: Cleans, transforms, and validates datasets using pandas. Use when preparing raw data for analysis, modeling, or export.
license: Apache-2.0
compatibility: Claude Code, Codex, Gemini CLI
metadata:
  author: ai-skills
  version: "1.0"
  category: data-analytics
  tags: pandas, data-cleaning, missing-values, duplicates, outliers, normalization
---

## Overview

Provides a complete, reusable pandas data cleaning pipeline for raw datasets. Covers missing value strategies (drop, fill, interpolate), duplicate detection and removal, dtype inference and safe casting, string normalization, outlier detection (IQR, Z-score, isolation forest), column renaming conventions, and a full end-to-end cleaning function template that can be dropped into notebooks or scripts.

## When to Use This Skill

- Receiving raw data from exports, APIs, or databases that needs preparation.
- Exploratory data analysis (EDA) before modeling.
- Building reproducible data preparation steps for ML or reporting.

## Prerequisites

- Python environment with pandas, numpy, and optionally scikit-learn for advanced outlier detection.
- The raw dataset (CSV, Parquet, DataFrame in memory, or SQL query result).
- Understanding of the domain (what "valid" looks like for each column).

## Steps

1. **Initial inspection**:
   - `df.head()`, `df.info()`, `df.describe(include='all')`, `df.isnull().sum()`.
   - Identify obvious issues (mixed types, weird strings, extreme values).

2. **Missing values strategy** (per column or group):
   - Drop rows/columns if <5% missing and not critical.
   - Fill with median/mean/mode for numeric.
   - Forward/backward fill or interpolate for time series.
   - "Unknown" or sentinel value for categorical.
   - Flag rows with missing critical fields.

3. **Duplicates**:
   - Exact duplicates: `drop_duplicates()`.
   - Fuzzy duplicates (same entity different spelling): use `recordlinkage` or simple key normalization + group.

4. **Dtype cleaning & casting**:
   - Infer dtypes safely.
   - Convert dates with `pd.to_datetime(errors='coerce')`.
   - Numeric with `pd.to_numeric(errors='coerce')`.
   - Categorical for low-cardinality strings.

5. **String normalization**:
   - `.str.strip().str.lower()`.
   - Remove accents, normalize unicode.
   - Standardize categories (map "USA", "U.S.", "United States" → "US").

6. **Outlier detection & treatment**:
   - IQR method for most numeric.
   - Z-score for near-normal distributions.
   - Domain-specific rules (negative age, price > 10x median, etc.).
   - Cap, clip, or flag rather than blindly remove.

7. **Column hygiene**:
   - Rename to snake_case, consistent naming.
   - Reorder columns logically.
   - Add derived columns (e.g., `is_weekend`, `age_group`).

8. **Validation**:
   - Assert expected columns, dtypes, row count range, no nulls in critical fields.
   - Great Expectations or custom checks.

9. **Output**:
   - Reusable `clean_data(df: pd.DataFrame) -> pd.DataFrame` function.
   - Before/after summary statistics.
   - Notebook cells or script that can be run on new files.
   - Export to Parquet/CSV with metadata.

## Examples

A complete cleaning pipeline for a typical customer/orders dataset (handle missing emails, normalize country codes, detect price outliers, deduplicate on customer_id + email, cast dates, add features) with before/after reports is included.

## Edge Cases & Error Handling

- **Mixed types in a column**: Coerce and report how many rows became NaN.
- **Very large files**: Use `chunksize` or Dask / Polars for out-of-core.
- **Time series specific**: Resample, forward fill with limits, detect gaps.

## Verification

1. Run the cleaner on the raw data — no errors.
2. `clean_df.isnull().sum()` shows only expected missing values.
3. `clean_df.dtypes` are correct.
4. Spot checks: random samples look reasonable.
5. Row count and key statistics are within expected ranges (or documented changes are explained).
6. Re-run on a new batch of raw data produces consistent output shape.
7. Success: The cleaned dataset is ready for analysis or modeling with documented transformations.

## References

- [Pandas User Guide - Working with missing data](https://pandas.pydata.org/docs/user_guide/missing_data.html)
- [Pandas Best Practices](https://pandas.pydata.org/docs/development/best_practices.html)
- [Data Cleaning with Python (book)](https://www.oreilly.com/library/view/data-cleaning-with/9781492056447/)
