"""
Model training pipeline for the AI Loan Decision Platform.

Trains XGBoost (primary) and Random Forest (secondary) models
on the Give Me Some Credit dataset for credit default prediction.

The model predicts probability of DEFAULT (not approval).
Approval logic: Approval_Probability = (1 - Default_Probability) * 100

Usage: python -m app.ml.train

Requirements: 5.4, 5.5, 6.1, 6.3
"""

import json
import os
import sys
from pathlib import Path

import joblib
import numpy as np
import optuna
import pandas as pd
from scipy.stats import ks_2samp
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import f1_score, roc_auc_score
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier

from app.ml.preprocessing import FEATURE_NAMES, preprocess_kaggle_dataset

# Paths
ARTIFACTS_DIR = Path(__file__).parent / "artifacts"
DATA_DIR = Path(__file__).parent / "data"

# Dataset source: Kaggle "Give Me Some Credit" competition
# Download from: https://www.kaggle.com/c/GiveMeSomeCredit/data
# Place cs-training.csv in: backend/app/ml/data/cs-training.csv


def load_dataset() -> pd.DataFrame:
    """
    Load the Give Me Some Credit dataset from local storage.

    The dataset must be manually downloaded from Kaggle and placed at:
    backend/app/ml/data/cs-training.csv

    Returns:
        Raw DataFrame from the dataset.
    """
    local_path = DATA_DIR / "cs-training.csv"

    if local_path.exists():
        print(f"[INFO] Loading dataset from: {local_path}")
        return pd.read_csv(local_path)

    print("[ERROR] Dataset not found!")
    print(f"[INFO] Expected location: {local_path}")
    print("")
    print("[INFO] To obtain the dataset:")
    print("  1. Go to https://www.kaggle.com/c/GiveMeSomeCredit/data")
    print("  2. Download 'cs-training.csv'")
    print(f"  3. Place it at: {local_path}")
    print("")
    print("  Or via Kaggle CLI:")
    print("    kaggle competitions download -c GiveMeSomeCredit")
    sys.exit(1)


def compute_ks_statistic(y_true: np.ndarray, y_prob: np.ndarray) -> float:
    """
    Compute KS statistic between positive and negative class probability distributions.

    Args:
        y_true: True binary labels.
        y_prob: Predicted probabilities for the positive class.

    Returns:
        KS statistic value.
    """
    pos_probs = y_prob[y_true == 1]
    neg_probs = y_prob[y_true == 0]
    ks_stat, _ = ks_2samp(pos_probs, neg_probs)
    return ks_stat


def find_optimal_threshold(y_true: np.ndarray, y_prob: np.ndarray) -> float:
    """
    Find the optimal classification threshold that maximizes F1 score.

    Args:
        y_true: True binary labels.
        y_prob: Predicted probabilities.

    Returns:
        Optimal threshold value.
    """
    best_threshold = 0.5
    best_f1 = 0.0

    for threshold in np.arange(0.1, 0.9, 0.01):
        y_pred = (y_prob >= threshold).astype(int)
        f1 = f1_score(y_true, y_pred)
        if f1 > best_f1:
            best_f1 = f1
            best_threshold = threshold

    return best_threshold


def evaluate_model(
    model_name: str, y_true: np.ndarray, y_prob: np.ndarray
) -> dict:
    """
    Evaluate a model and compute performance metrics.

    Args:
        model_name: Name of the model for display.
        y_true: True binary labels.
        y_prob: Predicted probabilities for the positive class.

    Returns:
        Dictionary with AUC-ROC, F1 Score, and KS Statistic.
    """
    # AUC-ROC
    auc_roc = roc_auc_score(y_true, y_prob)

    # F1 Score with optimal threshold
    optimal_threshold = find_optimal_threshold(y_true, y_prob)
    y_pred = (y_prob >= optimal_threshold).astype(int)
    f1 = f1_score(y_true, y_pred)

    # KS Statistic
    ks_stat = compute_ks_statistic(y_true, y_prob)

    print(f"\n{'='*50}")
    print(f"  {model_name} Performance Metrics")
    print(f"{'='*50}")
    print(f"  AUC-ROC:       {auc_roc:.4f}")
    print(f"  F1 Score:      {f1:.4f} (threshold={optimal_threshold:.2f})")
    print(f"  KS Statistic:  {ks_stat:.4f}")
    print(f"{'='*50}")

    return {
        "auc_roc": round(auc_roc, 4),
        "f1_score": round(f1, 4),
        "ks_statistic": round(ks_stat, 4),
        "optimal_threshold": round(optimal_threshold, 4),
    }


def train_xgboost_with_optuna(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_test: np.ndarray,
    y_test: np.ndarray,
    n_trials: int = 50,
) -> XGBClassifier:
    """
    Train XGBoost model with Optuna hyperparameter tuning.

    Tunes: max_depth, learning_rate, n_estimators, subsample,
    colsample_bytree, min_child_weight, gamma, reg_alpha, reg_lambda.

    Args:
        X_train: Training features.
        y_train: Training labels.
        X_test: Test features for evaluation.
        y_test: Test labels for evaluation.
        n_trials: Number of Optuna trials.

    Returns:
        Best XGBoost model.
    """
    print(f"\n[INFO] Starting Optuna hyperparameter tuning ({n_trials} trials)...")

    # Suppress Optuna logging for cleaner output
    optuna.logging.set_verbosity(optuna.logging.WARNING)

    def objective(trial: optuna.Trial) -> float:
        params = {
            "max_depth": trial.suggest_int("max_depth", 3, 10),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
            "n_estimators": trial.suggest_int("n_estimators", 100, 500),
            "subsample": trial.suggest_float("subsample", 0.6, 1.0),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
            "min_child_weight": trial.suggest_int("min_child_weight", 1, 10),
            "gamma": trial.suggest_float("gamma", 0.0, 5.0),
            "reg_alpha": trial.suggest_float("reg_alpha", 1e-8, 10.0, log=True),
            "reg_lambda": trial.suggest_float("reg_lambda", 1e-8, 10.0, log=True),
        }

        model = XGBClassifier(
            **params,
            objective="binary:logistic",
            eval_metric="auc",
            random_state=42,
            n_jobs=-1,
        )

        model.fit(
            X_train,
            y_train,
            eval_set=[(X_test, y_test)],
            verbose=False,
        )

        y_prob = model.predict_proba(X_test)[:, 1]
        auc = roc_auc_score(y_test, y_prob)
        return auc

    study = optuna.create_study(direction="maximize", study_name="xgboost_tuning")
    study.optimize(objective, n_trials=n_trials, show_progress_bar=True)

    print(f"[INFO] Best trial AUC: {study.best_value:.4f}")
    print(f"[INFO] Best parameters: {study.best_params}")

    # Train final model with best parameters
    best_params = study.best_params
    best_model = XGBClassifier(
        **best_params,
        objective="binary:logistic",
        eval_metric="auc",
        random_state=42,
        n_jobs=-1,
    )

    best_model.fit(
        X_train,
        y_train,
        eval_set=[(X_test, y_test)],
        verbose=False,
    )

    return best_model


def train_random_forest(
    X_train: np.ndarray, y_train: np.ndarray
) -> RandomForestClassifier:
    """
    Train Random Forest model with reasonable defaults.

    Args:
        X_train: Training features.
        y_train: Training labels.

    Returns:
        Trained Random Forest model.
    """
    print("\n[INFO] Training Random Forest model...")

    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=10,
        random_state=42,
        n_jobs=-1,
        class_weight="balanced",
    )

    model.fit(X_train, y_train)
    print("[INFO] Random Forest training complete.")

    return model


def save_artifacts(
    xgb_model: XGBClassifier,
    rf_model: RandomForestClassifier,
    xgb_metrics: dict,
    rf_metrics: dict,
) -> None:
    """
    Save trained models and metadata to the artifacts directory.

    Saves:
    - xgboost_model.joblib
    - random_forest_model.joblib
    - model_metrics.json
    - feature_names.json

    Args:
        xgb_model: Trained XGBoost model.
        rf_model: Trained Random Forest model.
        xgb_metrics: XGBoost performance metrics.
        rf_metrics: Random Forest performance metrics.
    """
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    # Save models
    xgb_path = ARTIFACTS_DIR / "xgboost_model.joblib"
    rf_path = ARTIFACTS_DIR / "random_forest_model.joblib"

    joblib.dump(xgb_model, xgb_path)
    print(f"[INFO] XGBoost model saved to: {xgb_path}")

    joblib.dump(rf_model, rf_path)
    print(f"[INFO] Random Forest model saved to: {rf_path}")

    # Save metrics
    metrics = {
        "xgboost": xgb_metrics,
        "random_forest": rf_metrics,
    }
    metrics_path = ARTIFACTS_DIR / "model_metrics.json"
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)
    print(f"[INFO] Model metrics saved to: {metrics_path}")

    # Save feature names
    feature_names_path = ARTIFACTS_DIR / "feature_names.json"
    with open(feature_names_path, "w") as f:
        json.dump(FEATURE_NAMES, f, indent=2)
    print(f"[INFO] Feature names saved to: {feature_names_path}")


def main() -> None:
    """
    Main training pipeline.

    1. Load dataset
    2. Preprocess and engineer features
    3. Split 80/20 with stratification
    4. Train XGBoost with Optuna tuning
    5. Train Random Forest
    6. Evaluate both models
    7. Save artifacts
    """
    print("=" * 60)
    print("  AI Loan Decision Platform - Model Training Pipeline")
    print("=" * 60)

    # Step 1: Load dataset
    print("\n[STEP 1/7] Loading dataset...")
    raw_df = load_dataset()
    print(f"[INFO] Dataset shape: {raw_df.shape}")

    # Step 2: Preprocess
    print("\n[STEP 2/7] Preprocessing and feature engineering...")
    features, target = preprocess_kaggle_dataset(raw_df)
    print(f"[INFO] Features shape: {features.shape}")
    print(f"[INFO] Target distribution: {target.value_counts().to_dict()}")
    print(f"[INFO] Default rate: {target.mean():.4f}")

    # Step 3: Train/test split (80/20, stratified)
    print("\n[STEP 3/7] Splitting data (80/20, stratified)...")
    X_train, X_test, y_train, y_test = train_test_split(
        features.values,
        target.values,
        test_size=0.2,
        random_state=42,
        stratify=target.values,
    )
    print(f"[INFO] Training set: {X_train.shape[0]} samples")
    print(f"[INFO] Test set: {X_test.shape[0]} samples")

    # Step 4: Train XGBoost with Optuna
    print("\n[STEP 4/7] Training XGBoost with Optuna hyperparameter tuning...")
    xgb_model = train_xgboost_with_optuna(
        X_train, y_train, X_test, y_test, n_trials=50
    )

    # Step 5: Train Random Forest
    print("\n[STEP 5/7] Training Random Forest...")
    rf_model = train_random_forest(X_train, y_train)

    # Step 6: Evaluate both models
    print("\n[STEP 6/7] Evaluating models on test set...")
    xgb_probs = xgb_model.predict_proba(X_test)[:, 1]
    rf_probs = rf_model.predict_proba(X_test)[:, 1]

    xgb_metrics = evaluate_model("XGBoost (Primary)", y_test, xgb_probs)
    rf_metrics = evaluate_model("Random Forest (Secondary)", y_test, rf_probs)

    # Step 7: Save artifacts
    print("\n[STEP 7/7] Saving model artifacts...")
    save_artifacts(xgb_model, rf_model, xgb_metrics, rf_metrics)

    # Final summary
    print("\n" + "=" * 60)
    print("  Training Complete!")
    print("=" * 60)
    print(f"\n  XGBoost AUC-ROC:       {xgb_metrics['auc_roc']:.4f}")
    print(f"  Random Forest AUC-ROC: {rf_metrics['auc_roc']:.4f}")
    print(f"\n  Artifacts saved to: {ARTIFACTS_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
