---
name: visualization-generator
description: Creates data visualizations using matplotlib, seaborn, plotly, or D3.js. Use when generating charts, graphs, dashboards, or exploratory data plots.
license: Apache-2.0
compatibility: Claude Code, Codex, Gemini CLI
metadata:
  author: ai-skills
  version: "1.0"
  category: data-analytics
  tags: visualization, matplotlib, seaborn, plotly, d3, charts, colorblind
---

## Overview

Generates appropriate, accessible, and publication-quality data visualizations. Includes a chart type selection guide, matplotlib/seaborn best practices, Plotly Express quick interactive charts, D3.js patterns for custom web visualizations, colorblind-safe palettes, proper labeling, and export options (PNG, SVG, HTML, interactive).

## When to Use This Skill

- Exploratory data analysis.
- Creating reports, dashboards, or presentations.
- The user asks for "a chart of...", "visualize this data", "plot the trend", etc.
- Need interactive web charts or static figures for papers/slides.

## Prerequisites

- Data in a pandas DataFrame, list of dicts, or JSON/CSV.
- Python environment with matplotlib, seaborn, plotly (or Node for D3).
- Understanding of the story the visualization should tell.

## Steps

1. **Chart type selection** (use the guide):
   - Comparison: bar, column, grouped bar.
   - Trend over time: line, area.
   - Distribution: histogram, box, violin, density.
   - Relationship: scatter, bubble, heatmap.
   - Composition: stacked bar, pie (use sparingly), treemap, sunburst.
   - Geospatial: choropleth, point map.

2. **Matplotlib / Seaborn setup**:
   - Use `seaborn.set_theme()` or a custom style.
   - Figure size appropriate for medium (6x4 to 10x6 inches for print).
   - Clear titles, axis labels, units.
   - Legend only when necessary; direct labels when possible.

3. **Color**:
   - Colorblind-safe palettes (seaborn `colorblind`, ColorBrewer, viridis, cividis).
   - Consistent colors across related charts.
   - High contrast for important categories.

4. **Plotly Express** (for interactive / dashboards):
   - `px.bar`, `px.line`, `px.scatter`, `px.histogram`, etc.
   - Faceting, animation, hover templates.
   - Export to HTML for embedding.

5. **D3.js** (for custom web viz):
   - Data join pattern (`selectAll().data().join()`).
   - Scales, axes, transitions.
   - Provide a minimal self-contained example (index.html + script).

6. **Accessibility & clarity**:
   - Sufficient contrast.
   - Text labels (not just color or position).
   - Alt text or aria descriptions for web charts.
   - Avoid 3D, excessive animation, pie charts for >5 categories.

7. **Output**:
   - Complete, runnable code for the chosen chart(s).
   - The figure saved to file or displayed.
   - Interactive HTML version when using Plotly.
   - Notes on how to update with new data.

## Examples

- Seaborn bar + line combo for sales by category over time.
- Plotly interactive scatter with hover and animation by year.
- D3.js bar chart with tooltips and responsive sizing.
- Heatmap for correlation matrix.
- All with proper titles, labels, colorblind palettes, and export code.

## Edge Cases & Error Handling

- **Very large datasets**: Sample or use datashader / WebGL in Plotly.
- **Many categories**: Group "other" or use a treemap/sunburst.
- **Negative + positive values**: Diverging color scale.
- **Time series with gaps**: Connect or show gaps explicitly.

## Verification

1. Run the code — chart renders without error.
2. Visual inspection: labels readable, no overlapping text, colors distinguishable.
3. Colorblind simulation (e.g., Coblis or browser extension) — still interpretable.
4. For interactive: hover, zoom, legend toggle work.
5. Export and re-open the image/SVG/HTML — quality preserved.
6. Success: The visualization accurately and clearly communicates the intended insight.

## References

- [Seaborn](https://seaborn.pydata.org/)
- [Plotly Express](https://plotly.com/python/plotly-express/)
- [Matplotlib](https://matplotlib.org/)
- [D3.js Gallery](https://observablehq.com/@d3/gallery)
- [ColorBrewer](https://colorbrewer2.org/)
- [Fundamentals of Data Visualization (book)](https://clauswilke.com/dataviz/)
