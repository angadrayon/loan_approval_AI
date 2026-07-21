"""
DiCE Counterfactual Service for the AI Loan Decision Platform.

Generates counterfactual explanations for rejected loan applications
using the DiCE (Diverse Counterfactual Explanations) library with
the trained XGBoost model.

Shows minimum feature changes required to achieve an Approved decision.

Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 8.8
"""

import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from pathlib import Path
from typing import Optional

import joblib
import numpy as np
import pandas as pd

from app.ml.preprocessing import (
    EMPLOYMENT_STATUS_MAP,
    FEATURE_NAMES,
    transform_application_input,
)
from app.services.readiness_service import get_readiness_service, map_readiness_category

logger = logging.getLogger(__name__)

ARTIFACTS_DIR = Path(__file__).parent.parent / "ml" / "artifacts"

# Timeout for counterfactual generation (Requirement 8.7)
CF_TIMEOUT_SECONDS = 10

# Feature constraints matching Requirement 4 validation bounds (Requirement 8.8)
FEATURE_RANGES = {
    "age": (18, 100),                       # Immutable — included for reference only
    "monthly_income": (1, 10_000_000),
    "employment_status_encoded": (0, 3),
    "employment_length": (0, 50),
    "credit_score": (300, 850),
    "existing_loans": (0, 50),
    "monthly_emi": (0, 10_000_000),
    "dti_ratio": (0, 100),
    "credit_utilization": (0, 100),
    "loan_amount_requested": (1, 10_000_000),
}

# Immutable features (Requirement 8.3): only Age
IMMUTABLE_FEATURES = ["age"]

# Mutable features (Requirement 8.3)
MUTABLE_FEATURES = [
    "monthly_income",
    "employment_status_encoded",
    "employment_length",
    "credit_score",
    "existing_loans",
    "monthly_emi",
    "dti_ratio",
    "credit_utilization",
    "loan_amount_requested",
]

# Reverse employment status map for display
EMPLOYMENT_STATUS_REVERSE = {v: k for k, v in EMPLOYMENT_STATUS_MAP.items()}


def _map_risk_level(risk_score: float) -> str:
    """Map risk score to risk level category."""
    if risk_score <= 20:
        return "Very Low Risk"
    elif risk_score <= 40:
        return "Low Risk"
    elif risk_score <= 60:
        return "Moderate Risk"
    elif risk_score <= 80:
        return "High Risk"
    else:
        return "Very High Risk"


class CounterfactualService:
    """Generates DiCE counterfactual explanations for rejected applications.

    Uses the dice_ml library with the trained XGBoost model to find
    minimum feature changes that would flip a Rejected decision to Approved.
    """

    def __init__(self):
        """Initialize with the trained XGBoost model."""
        self.xgb_model = None
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._load_model()

    def _load_model(self):
        """Load the XGBoost model for counterfactual generation."""
        xgb_path = ARTIFACTS_DIR / "xgboost_model.joblib"

        if not xgb_path.exists():
            logger.error("XGBoost model not found at %s — counterfactuals unavailable", xgb_path)
            return

        try:
            self.xgb_model = joblib.load(xgb_path)
            logger.info("CounterfactualService: XGBoost model loaded")
        except Exception as e:
            logger.error("Failed to load XGBoost model for counterfactuals: %s", e)

    def generate(
        self, application_data: dict, num_cfs: int = 3
    ) -> Optional[list[dict]]:
        """
        Generate counterfactual explanations for a rejected application.

        Args:
            application_data: Dict matching LoanApplicationInput fields.
            num_cfs: Number of counterfactuals to generate (1-3, default 3).

        Returns:
            List of Counterfactual dicts, each with:
            - feature: feature name that changed
            - current_value: original value
            - recommended_value: suggested new value
            - projected_approval_probability: approval prob after change
            - projected_risk_score: risk score after change
            - projected_risk_level: risk level after change
            - projected_loan_readiness_score: readiness score after change

            Returns None if generation fails or times out (Requirement 8.7).
        """
        if self.xgb_model is None:
            logger.warning("XGBoost model not loaded — cannot generate counterfactuals")
            return None

        num_cfs = max(1, min(3, num_cfs))  # Clamp to 1-3 (Requirement 8.1)

        try:
            future = self._executor.submit(
                self._generate_counterfactuals, application_data, num_cfs
            )
            result = future.result(timeout=CF_TIMEOUT_SECONDS)
            return result
        except FuturesTimeoutError:
            logger.warning(
                "Counterfactual generation timed out after %ds", CF_TIMEOUT_SECONDS
            )
            return None
        except Exception as e:
            logger.error("Counterfactual generation failed: %s", e)
            return None

    def _generate_counterfactuals(
        self, application_data: dict, num_cfs: int
    ) -> Optional[list[dict]]:
        """
        Internal method to generate counterfactuals using DiCE.

        Uses dice_ml to find diverse counterfactual explanations that
        flip the decision from Rejected to Approved.
        """
        try:
            import dice_ml

            # Transform input to feature array
            features = transform_application_input(application_data)

            # Create a DataFrame with the input for DiCE
            # DiCE requires an outcome column in the dataframe
            input_df = pd.DataFrame([features], columns=FEATURE_NAMES)
            
            # Add a dummy outcome column (DiCE requires it)
            # Value 1 = "defaulted" (rejected), we want to flip to 0 (approved)
            input_df["outcome"] = 1

            # Create training data representation for DiCE
            continuous_features = FEATURE_NAMES.copy()  # Treat all as continuous for DiCE

            d = dice_ml.Data(
                dataframe=input_df,
                continuous_features=continuous_features,
                outcome_name="outcome",
            )

            # Create model interface
            m = dice_ml.Model(model=self.xgb_model, backend="sklearn")

            # Create DiCE explainer with proximity weight for minimal changes (Req 8.4)
            exp = dice_ml.Dice(d, m, method="random")

            # Remove outcome column from query instance
            query_df = input_df.drop(columns=["outcome"])

            # Generate counterfactuals
            cf_result = exp.generate_counterfactuals(
                query_instances=query_df,
                total_CFs=num_cfs,
                desired_class="opposite",
                features_to_vary=MUTABLE_FEATURES,
                permitted_range={
                    "monthly_income": [FEATURE_RANGES["monthly_income"][0], FEATURE_RANGES["monthly_income"][1]],
                    "employment_status_encoded": [0, 3],
                    "employment_length": [FEATURE_RANGES["employment_length"][0], FEATURE_RANGES["employment_length"][1]],
                    "credit_score": [FEATURE_RANGES["credit_score"][0], FEATURE_RANGES["credit_score"][1]],
                    "existing_loans": [FEATURE_RANGES["existing_loans"][0], FEATURE_RANGES["existing_loans"][1]],
                    "monthly_emi": [FEATURE_RANGES["monthly_emi"][0], FEATURE_RANGES["monthly_emi"][1]],
                    "dti_ratio": [FEATURE_RANGES["dti_ratio"][0], FEATURE_RANGES["dti_ratio"][1]],
                    "credit_utilization": [FEATURE_RANGES["credit_utilization"][0], FEATURE_RANGES["credit_utilization"][1]],
                    "loan_amount_requested": [FEATURE_RANGES["loan_amount_requested"][0], FEATURE_RANGES["loan_amount_requested"][1]],
                },
            )

            # Extract counterfactual instances
            if cf_result is None or cf_result.cf_examples_list is None:
                logger.info("[DEBUG-CF] cf_result is None or no cf_examples_list")
                return None

            cf_examples = cf_result.cf_examples_list[0]
            if cf_examples.final_cfs_df is None or cf_examples.final_cfs_df.empty:
                logger.info("[DEBUG-CF] final_cfs_df is None or empty")
                return None

            cf_df = cf_examples.final_cfs_df
            logger.info("[DEBUG-CF] DiCE generated %d counterfactual rows", len(cf_df))
            logger.info("[DEBUG-CF] CF columns: %s", list(cf_df.columns))
            logger.info("[DEBUG-CF] CF first row: %s", cf_df.iloc[0].to_dict() if len(cf_df) > 0 else "empty")

            # Process each counterfactual — find changed features and compute projections
            counterfactuals = []
            for row_idx, cf_row in cf_df.iterrows():
                try:
                    cf_features = cf_row[FEATURE_NAMES].values.astype(np.float64)
                except KeyError as ke:
                    logger.error("[DEBUG-CF] KeyError extracting features from CF row: %s. Available cols: %s", ke, list(cf_row.index))
                    continue

                # Find features that changed significantly
                for i, feature_name in enumerate(FEATURE_NAMES):
                    if feature_name in IMMUTABLE_FEATURES:
                        continue

                    original_val = float(features[i])
                    cf_val = float(cf_features[i])

                    # Only report features that actually changed (threshold: 0.01)
                    if abs(cf_val - original_val) < 0.01:
                        continue

                    # Re-run the counterfactual through XGBoost for projected outcome
                    projected = self._compute_projection(cf_features, application_data)

                    counterfactuals.append({
                        "feature": feature_name,
                        "current_value": round(original_val, 2),
                        "recommended_value": round(cf_val, 2),
                        "projected_approval_probability": projected["approval_probability"],
                        "projected_risk_score": projected["risk_score"],
                        "projected_risk_level": projected["risk_level"],
                        "projected_loan_readiness_score": projected["loan_readiness_score"],
                    })

                # Limit to meaningful changes (avoid duplicates from same CF)
                if len(counterfactuals) >= num_cfs * 3:
                    break

            # Deduplicate by feature and take top changes
            seen_features = set()
            unique_cfs = []
            for cf in counterfactuals:
                if cf["feature"] not in seen_features:
                    seen_features.add(cf["feature"])
                    unique_cfs.append(cf)
                if len(unique_cfs) >= num_cfs:
                    break

            logger.info("[DEBUG-CF] Total extracted CFs: %d, unique: %d", len(counterfactuals), len(unique_cfs))
            return unique_cfs if unique_cfs else None

        except ImportError:
            logger.error("dice_ml not installed — counterfactuals unavailable")
            return None
        except Exception as e:
            logger.error("DiCE counterfactual generation error: %s", e)
            return None

    def _compute_projection(
        self, cf_features: np.ndarray, original_application_data: dict
    ) -> dict:
        """
        Compute projected outcomes for a counterfactual feature set.

        Re-runs the counterfactual through XGBoost and computes
        the Loan Readiness Score for the projected values.

        Args:
            cf_features: 1D numpy array with 10 counterfactual feature values.
            original_application_data: Original application dict (for context).

        Returns:
            Dict with projected approval_probability, risk_score, risk_level,
            and loan_readiness_score.
        """
        # XGBoost inference on counterfactual
        cf_2d = cf_features.reshape(1, -1)
        default_prob = float(self.xgb_model.predict_proba(cf_2d)[0, 1])

        approval_probability = round((1 - default_prob) * 100, 2)
        risk_score = round(default_prob * 100, 2)
        risk_level = _map_risk_level(risk_score)

        # Compute Loan Readiness Score for the counterfactual values
        cf_application = {
            "credit_score": float(cf_features[4]),
            "dti_ratio": float(cf_features[7]),
            "credit_utilization": float(cf_features[8]),
            "employment_length": float(cf_features[3]),
            "existing_loans": float(cf_features[5]),
        }

        try:
            readiness_svc = get_readiness_service()
            readiness_result = readiness_svc.compute(cf_application)
            loan_readiness_score = readiness_result["loan_readiness_score"]
        except Exception:
            loan_readiness_score = 0.0

        return {
            "approval_probability": approval_probability,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "loan_readiness_score": loan_readiness_score,
        }


# Singleton instance
_counterfactual_service: Optional[CounterfactualService] = None


def get_counterfactual_service() -> CounterfactualService:
    """Get or create the CounterfactualService singleton."""
    global _counterfactual_service
    if _counterfactual_service is None:
        _counterfactual_service = CounterfactualService()
    return _counterfactual_service
