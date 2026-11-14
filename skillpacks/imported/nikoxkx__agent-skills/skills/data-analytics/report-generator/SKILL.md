---
name: report-generator
description: Generates formatted data reports in PDF, Excel, or HTML from structured data. Use when producing recurring business reports, dashboards, or data summaries.
license: Apache-2.0
compatibility: Claude Code, Codex, Gemini CLI
metadata:
  author: ai-skills
  version: "1.0"
  category: data-analytics
  tags: reporting, pdf, excel, html, jinja, reportlab, openpyxl, scheduled
---

## Overview

Builds automated, professional reports from data. Covers report architecture (data layer, transform layer, template layer), PDF generation with ReportLab or WeasyPrint, Excel with openpyxl (formulas, charts, formatting), HTML reports with Jinja2 + CSS (for email or web), embedding charts, and scheduling/delivery (cron + email/Slack).

## When to Use This Skill

- Creating weekly/monthly business reports (sales, finance, operations, marketing).
- Generating customer-facing statements or invoices (see also `invoice-generator`).
- Automating dashboard exports or stakeholder updates.

## Prerequisites

- Structured data (SQL query result, pandas DataFrame, or JSON).
- Python environment with the chosen libraries (reportlab, openpyxl, jinja2, matplotlib/seaborn/plotly for charts).
- SMTP or Slack/Teams webhook for delivery (if automated).

## Steps

1. **Report architecture**:
   - Data layer: SQL or API calls (parameterized by date range, filters).
   - Transform layer: pandas cleaning, aggregation, KPI calculation.
   - Presentation layer: template + rendering engine.

2. **PDF (ReportLab or WeasyPrint)**:
   - ReportLab for pixel-perfect control (tables, charts, branding).
   - WeasyPrint for HTML/CSS → PDF (easier styling if you have web designers).
   - Include header/footer, page numbers, charts (embed PNG or use reportlab graphics).

3. **Excel (openpyxl)**:
   - Multiple sheets (Summary, Detail, Charts).
   - Formulas instead of static values where useful.
   - Conditional formatting, number formats, freeze panes.
   - Charts (bar, line, pie) via openpyxl.chart.
   - Professional styling (fonts, colors, borders from brand guidelines).

4. **HTML (Jinja2)**:
   - Reusable base template + sections.
   - Inline CSS for email compatibility.
   - Embed base64 images or link to hosted images.
   - Good for email reports or internal web dashboards.

5. **Charts**:
   - Generate with matplotlib/seaborn → save to BytesIO → embed.
   - Or Plotly → HTML (for interactive HTML reports).

6. **Scheduling & delivery**:
   - Cron or Airflow DAG.
   - Generate → attach to email (smtplib or SendGrid) or post to Slack.
   - Include "generated at" timestamp and data as-of date.

7. **Output**:
   - Complete Python script or notebook that produces the report.
   - Template files (`.html` for Jinja, or pure Python for ReportLab).
   - Example data.
   - Cron / Airflow example for automation.
   - Delivery script.

## Examples

A complete weekly sales report generator that produces:
- A branded PDF with summary KPIs, table, and two charts.
- An Excel version with multiple sheets and embedded charts.
- An HTML email version.
All from the same pandas DataFrames, with scheduling notes.

## Edge Cases & Error Handling

- **No data for the period**: Still produce a report with "No activity" messaging and previous period comparison.
- **Large reports**: Paginate or split into multiple files; use streaming where possible.
- **Email size limits**: Generate PDF/Excel and link to a secure download instead of attaching for very large reports.

## Verification

1. Run the generator with sample data — all three formats (PDF, Excel, HTML) are produced.
2. Open PDF — looks professional, charts render, numbers match source data.
3. Open Excel — formulas calculate, charts are present, formatting is clean.
4. HTML email renders correctly in Gmail/Outlook (test with Litmus or similar if possible).
5. Scheduled run succeeds and delivers.
6. Success: Stakeholders receive accurate, well-formatted reports on schedule with minimal manual work.

## References

- [ReportLab](https://www.reportlab.com/)
- [openpyxl](https://openpyxl.readthedocs.io/)
- [Jinja2](https://jinja.palletsprojects.com/)
- [WeasyPrint](https://weasyprint.org/)
- [Plotly for reports](https://plotly.com/python/)
