---
name: ml-model-trainer
description: Trains a traditional ML model (classification, regression, clustering) using scikit-learn or PyTorch. Use when building predictive models on tabular or structured data.
license: Apache-2.0
compatibility: Claude Code, Codex, Gemini CLI
metadata:
  author: ai-skills
  version: "1.0"
  category: ai-ml
  tags: machine-learning, scikit-learn, pytorch, classification, regression, clustering, pipeline
---

## Overview

Trains, evaluates, and serializes traditional machine learning models for tabular/structured data. Covers problem type identification, feature engineering checklist, model selection with tradeoffs, hyperparameter tuning (GridSearch, Optuna), cross-validation, evaluation metrics by problem type, full scikit-learn Pipeline, model serialization (joblib / pickle / ONNX), and a complete end-to-end training script template.

## When to Use This Skill

- Building a predictive model on tabular data (CSV, database, features from other systems).
- The user has "a dataset with labels" or "predict X from these features".
- You need something interpretable and fast to train/infer (as opposed to deep learning or LLMs).

## Prerequisites

- Cleaned tabular dataset (pandas DataFrame) with target variable.
- Python with `scikit-learn`, `pandas`, `numpy`, `joblib`. Optionally `optuna`, `xgboost`, `lightgbm`, `catboost`, `pytorch`.
- Understanding of the business problem (what "good" looks like).

## Steps

1. **Problem framing**:
   - Classification (binary, multiclass, multilabel)?
   - Regression (continuous target)?
   - Clustering (no labels, find groups)?
   - Time-series specific considerations?

2. **Feature engineering checklist**:
   - Handle missing values (imputer in pipeline).
   - Encode categoricals (OneHot, Target, Ordinal — choose per cardinality).
   - Scale numeric features (StandardScaler, RobustScaler).
   - Create interactions, polynomial features, date/time features, aggregations.
   - Feature selection (mutual info, permutation importance, or model-based).

3. **Model selection** (with tradeoffs):
   - Baseline: Dummy / Linear / Logistic.
   - Tree-based: RandomForest, XGBoost, LightGBM, CatBoost (often win on tabular).
   - Linear models for interpretability / speed.
   - Neural nets (MLP or more advanced) only when data volume justifies.

4. **Cross-validation & tuning**:
   - StratifiedKFold for classification.
   - TimeSeriesSplit for time-ordered data.
   - GridSearchCV or (better) Optuna for hyperparameter search.
   - Nested CV when you need unbiased performance estimate.

5. **Evaluation** (choose the right metrics):
   - Classification: Accuracy, Precision/Recall/F1 (per class + macro), ROC-AUC, PR-AUC, confusion matrix, calibration.
   - Regression: MAE, RMSE, R², MAPE (be careful with zeros).
   - Clustering: Silhouette, Davies-Bouldin, or downstream task performance.

6. **Full Pipeline**:
   - Use `sklearn.pipeline.Pipeline` + `ColumnTransformer` so preprocessing is fitted only on train and applied consistently.
   - Include the final estimator.

7. **Serialization & serving**:
   - `joblib.dump(pipeline, 'model.joblib')`.
   - ONNX for cross-platform / faster inference.
   - Simple FastAPI or Flask wrapper for real-time serving.
   - Batch scoring script.

8. **Output**:
   - Complete `train.py` that loads data → builds pipeline → tunes → evaluates → saves model + metrics.
   - Feature importance plot (for tree models).
   - Evaluation report (Markdown or notebook).
   - Inference example code.
   - Notes on monitoring (data drift, prediction drift).

## Examples

A full end-to-end script for a customer churn classification problem (tabular features): preprocessing with ColumnTransformer, LightGBM + Optuna tuning, cross-validation, SHAP importance, model save, and a simple prediction function is included. Similar template for regression and clustering.

## Edge Cases & Error Handling

- **Class imbalance**: Use `class_weight`, SMOTE (carefully), or appropriate metrics (not accuracy).
- **Data leakage**: Pipeline ensures no leakage; be extra careful with time-based features.
- **Categorical with high cardinality**: Target encoding with smoothing or embeddings.

## Verification

1. The training script runs end-to-end and produces a saved model.
2. Cross-validation scores are reasonable and stable.
3. On a held-out test set, performance matches or exceeds the CV estimate.
4. The pipeline can be loaded in a fresh environment and used to predict on new data with identical preprocessing.
5. Feature importance or SHAP values make business sense.
6. Success: You have a validated, serialized model that can be deployed and monitored.

## References

- [scikit-learn User Guide](https://scikit-learn.org/stable/user_guide.html)
- [Hands-On Machine Learning (book)](https://www.oreilly.com/library/view/hands-on-machine-learning/9781492032632/)
- [Optuna](https://optuna.org/)
- [XGBoost / LightGBM / CatBoost docs](https://xgboost.readthedocs.io/)
- [SHAP](https://shap.readthedocs.io/)
- [MLflow or DVC for experiment tracking](https://mlflow.org/)
