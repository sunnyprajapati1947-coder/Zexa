---
name: time-series-analyzer
description: Analyzes time series data for trends, seasonality, anomalies, and forecasting. Use when working with timestamped data like metrics, sales, or sensor readings.
license: Apache-2.0
compatibility: Claude Code, Codex, Gemini CLI
metadata:
  author: ai-skills
  version: "1.0"
  category: data-analytics
  tags: time-series, forecasting, seasonality, anomaly-detection, prophet, statsmodels
---

## Overview

Analyzes time series data for trends, seasonality, anomalies, and produces forecasts. Covers resampling and aggregation, rolling statistics, STL decomposition, anomaly detection (statistical and ML), basic ARIMA, and Facebook Prophet integration with visualization patterns suitable for dashboards or reports.

## When to Use This Skill

- Analyzing metrics, sales, sensor data, web traffic, or financial time series.
- Detecting anomalies or seasonality.
- Building short-to-medium term forecasts.
- The user provides timestamped data and asks for "trend", "seasonality", "anomaly", or "forecast".

## Prerequisites

- Time series data with a datetime column (pandas DataFrame with DatetimeIndex recommended).
- Python with `pandas`, `statsmodels`, `prophet` (or `neuralprophet`), `matplotlib`/`plotly`.
- For production forecasting: historical data of sufficient length (at least 2-3 full seasons).

## Steps

1. **Prepare the series**:
   - Set DatetimeIndex, sort.
   - Handle missing timestamps (resample + asfreq or interpolate).
   - Aggregate to the desired frequency (daily, hourly, etc.).

2. **Exploratory analysis**:
   - Line plot of raw series.
   - Rolling mean / std (7d, 30d).
   - Seasonal decomposition (statsmodels `seasonal_decompose` or STL).

3. **Anomaly detection**:
   - Statistical: IQR or Z-score on residuals after decomposition.
   - Simple: values outside rolling mean ± 3*std.
   - More robust: Isolation Forest or Prophet's built-in anomaly detection.

4. **Forecasting**:
   - Prophet (easy, handles seasonality/holidays well): `from prophet import Prophet`.
   - ARIMA / SARIMA via statsmodels (when you need more control or have domain knowledge).
   - Evaluate with train/test split + metrics (MAE, RMSE, MAPE).

5. **Visualization**:
   - Original + forecast with confidence interval.
   - Components plot (trend, weekly, yearly).
   - Anomaly overlay (red points on the line).

6. **Output**:
   - Complete analysis notebook or script.
   - Prophet model fit + forecast DataFrame.
   - Anomaly table with timestamps and scores.
   - Ready-to-embed Plotly or matplotlib figures.
   - Guidance on retraining cadence and monitoring forecast accuracy.

## Examples

A full end-to-end analysis of daily sales data: decomposition, anomaly detection (holiday spikes and dips flagged), Prophet 30-day forecast with components, and a dashboard-style Plotly figure is included.

## Edge Cases & Error Handling

- **Irregular or sparse data**: Resample with appropriate method; consider interpolation limits.
- **Strong external drivers** (promotions, outages): Add regressors to Prophet or use a more advanced model.
- **Non-stationary series**: Differencing or explicit trend modeling.
- **Very long horizons**: Warn that accuracy degrades; prefer shorter horizons or ensemble methods.

## Verification

1. The decomposition looks reasonable (trend, seasonal, residual separated).
2. Anomalies flagged match obvious outliers in a visual plot.
3. Forecast on a hold-out set has reasonable error metrics (document them).
4. Components plot shows expected weekly/yearly patterns.
5. Re-running with new data produces updated forecast without errors.
6. Success: The analysis reveals real trends/seasonality/anomalies and the forecast is usable for planning.

## References

- [Prophet](https://facebook.github.io/prophet/)
- [statsmodels Time Series](https://www.statsmodels.org/stable/tsa.html)
- [STL Decomposition](https://www.statsmodels.org/stable/generated/statsmodels.tsa.seasonal.STL.html)
- [Forecasting: Principles and Practice (book)](https://otexts.com/fpp3/)
