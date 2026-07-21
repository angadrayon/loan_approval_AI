"""
SHAP Explainer Service for the AI Loan Decision Platform.

Uses shap.TreeExplainer with the trained XGBoost model to compute
local and global SHAP explanations for predictions.

Requirements: 7.1, 7.2, 7.3, 7.4, 7.6
"""

import logging
from pathlib import Path
from typing import Optional

import joblib
import numpy as np
import shap

from app.ml.preprocessing import FEATURE_NAMES, transform_application_input

logger = logging.getLogger(__name__)

ARTIFACTS_DIR = Path(__file__).parent.parent / "ml" / "artifacts"


class ShapExplainerService:
    """Computes SHAP values for predictions using TreeExplainer.

    Provides local explanations (per-prediction) and global feature
    importance (across all stored predictions).
    """

    def __init__(self):
        """Initialize the SHAP explainer with the trained XGBoost model."""
        self.explainer: Optional[shap.TreeExplainer] = None
        self._load_explainer()

    def _load_explainer(self):
        """Load the XGBoost model and create a TreeExplainer."""
        xgb_path = ARTIFACTS_DIR / "xgboost_model.joblib"

        if not xgb_path.exists():
            logger.error("XGBoost model not found at %s — SHAP unavailable", xgb_path)
            return

        try:
            xgb_model = joblib.load(xgb_path)
            self.explainer = shap.TreeExplainer(xgb_model)
            logger.info("SHAP TreeExplainer initialized successfully")
        except Exception as e:
            logger.error("Failed to initialize SHAP TreeExplainer: %s", e)

    def compute_local_shap(
        self, application_data: dict
    ) -> Optional[list[dict]]:
        """
        Compute local SHAP values for a single prediction.

        Returns exactly 10 ShapValue objects (one per feature) with:
        - feature: feature name
        - value: the input feature value
        - shap_value: SHAP contribution magnitude
        - direction: "positive" or "negative"

        Args:
            application_data: Dict matching LoanApplicationInput fields.

        Returns:
            List of 10 ShapValue dicts sorted by absolute SHAP magnitude (descending),
            or None if SHAP computation fails.
        """
        if self.explainer is None:
            logger.warning("SHAP explainer not available — returning None")
            return None

        try:
            # Transform input to model-ready array
            features = transform_application_input(application_data)
            features_2d = features.reshape(1, -1)

            # Compute SHAP values
            shap_values = self.explainer.shap_values(features_2d)

            # TreeExplainer for binary classification may return a list [class_0, class_1]
            # or a single array. We want SHAP values for the positive class (default=1).
            if isinstance(shap_values, list):
                # Binary classification: use class 1 (default probability)
                shap_array = shap_values[1][0]
            elif shap_values.ndim == 3:
                # Shape (1, n_features, n_classes) — take class 1
                shap_array = shap_values[0, :, 1]
            else:
                # Shape (1, n_features) — single output
                shap_array = shap_values[0]

            # Build ShapValue objects
            # Note: SHAP values for default probability — negative SHAP = helps approval
            # We invert direction: positive SHAP (increases default) = negative for approval
            result = []
            for i, feature_name in enumerate(FEATURE_NAMES):
                raw_shap = float(shap_array[i])
                # Direction relative to APPROVAL (not default):
                # If SHAP value is negative (reduces default prob), it helps approval → "positive"
                # If SHAP value is positive (increases default prob), it hurts approval → "negative"
                direction = "positive" if raw_shap < 0 else "negative"

                result.append({
                    "feature": feature_name,
                    "value": float(features[i]),
                    "shap_value": abs(raw_shap),
                    "direction": direction,
                })

            # Sort by absolute SHAP value magnitude (descending)
            result.sort(key=lambda x: x["shap_value"], reverse=True)

            return result

        except Exception as e:
            logger.error("SHAP computation failed: %s", e)
            return None

    def get_top_factors(
        self, shap_values: list[dict], n: int = 3
    ) -> list[dict]:
        """
        Extract the top N most influential factors from SHAP values.

        Args:
            shap_values: List of ShapValue dicts (already sorted by magnitude).
            n: Number of top factors to return (default 3).

        Returns:
            List of top N ShapValue dicts by absolute SHAP magnitude.
        """
        return shap_values[:n]

    def compute_global_importance(
        self, all_features: list[np.ndarray]
    ) -> Optional[list[dict]]:
        """
        Compute global feature importance across multiple predictions.

        Computes mean absolute SHAP values across all provided feature arrays.

        Args:
            all_features: List of 1D numpy arrays (each with 10 features).

        Returns:
            List of dicts with feature name and mean absolute SHAP value,
            sorted by importance descending. Returns None on failure.
        """
        if self.explainer is None:
            logger.warning("SHAP explainer not available — returning None")
            return None

        if not all_features:
            return []

        try:
            # Stack all features into a 2D array
            features_2d = np.vstack(all_features)

            # Compute SHAP values for all samples
            shap_values = self.explainer.shap_values(features_2d)

            # Handle binary classification output format
            if isinstance(shap_values, list):
                shap_matrix = shap_values[1]  # class 1 (default)
            elif shap_values.ndim == 3:
                shap_matrix = shap_values[:, :, 1]
            else:
                shap_matrix = shap_values

            # Compute mean absolute SHAP value per feature
            mean_abs_shap = np.mean(np.abs(shap_matrix), axis=0)

            result = []
            for i, feature_name in enumerate(FEATURE_NAMES):
                result.append({
                    "feature": feature_name,
                    "importance": round(float(mean_abs_shap[i]), 6),
                })

            # Sort by importance descending
            result.sort(key=lambda x: x["importance"], reverse=True)

            return result

        except Exception as e:
            logger.error("Global SHAP computation failed: %s", e)
            return None


# Singleton instance
_shap_service: Optional[ShapExplainerService] = None


def get_shap_service() -> ShapExplainerService:
    """Get or create the ShapExplainerService singleton."""
    global _shap_service
    if _shap_service is None:
        _shap_service = ShapExplainerService()
    return _shap_service
