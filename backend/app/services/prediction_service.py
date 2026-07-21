"""
PredictionService — orchestrates the ML prediction pipeline.

Loads trained XGBoost and Random Forest models at initialization,
provides predict() and simulate() methods for inference.

Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 10.2
"""

import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np

from app.ml.preprocessing import transform_application_input

logger = logging.getLogger(__name__)

ARTIFACTS_DIR = Path(__file__).parent.parent / "ml" / "artifacts"

# Timeout for inference in seconds (Requirement 5.6)
INFERENCE_TIMEOUT_SECONDS = 5


def map_risk_level(risk_score: float) -> str:
    """Map numeric risk score (0-100) to categorical risk level.

    Categories (Requirement 5.2):
        - Very Low Risk: 0-20
        - Low Risk: 21-40
        - Moderate Risk: 41-60
        - High Risk: 61-80
        - Very High Risk: 81-100
    """
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


class PredictionService:
    """Orchestrates the ML prediction pipeline.

    Loads trained XGBoost and Random Forest models from the artifacts
    directory and provides predict() and simulate() methods for inference.
    """

    def __init__(self):
        """Load trained models from artifacts directory."""
        self.xgb_model = None
        self.rf_model = None
        self._executor = ThreadPoolExecutor(max_workers=2)
        self._load_models()

    def _load_models(self):
        """Load serialized models from disk.

        Handles missing model files gracefully by logging errors
        without crashing the application.
        """
        xgb_path = ARTIFACTS_DIR / "xgboost_model.joblib"
        rf_path = ARTIFACTS_DIR / "random_forest_model.joblib"

        if xgb_path.exists():
            try:
                self.xgb_model = joblib.load(xgb_path)
                logger.info("XGBoost model loaded from %s", xgb_path)
            except Exception as e:
                logger.error("Failed to load XGBoost model: %s", e)
        else:
            logger.error("XGBoost model not found at %s", xgb_path)

        if rf_path.exists():
            try:
                self.rf_model = joblib.load(rf_path)
                logger.info("Random Forest model loaded from %s", rf_path)
            except Exception as e:
                logger.error("Failed to load Random Forest model: %s", e)
        else:
            logger.error("Random Forest model not found at %s", rf_path)

    def _run_inference(self, application_data: dict) -> dict:
        """Run the core inference logic (XGBoost + Random Forest).

        Args:
            application_data: Dict matching LoanApplicationInput fields.

        Returns:
            Dict with all prediction metrics.
        """
        # Transform input to model-ready array
        features = transform_application_input(application_data)
        features_2d = features.reshape(1, -1)

        # XGBoost inference — outputs probability of DEFAULT
        xgb_default_prob = float(self.xgb_model.predict_proba(features_2d)[0, 1])

        # Compute derived metrics (Requirement 5.1)
        approval_probability = (1 - xgb_default_prob) * 100
        risk_score = xgb_default_prob * 100
        risk_level = map_risk_level(risk_score)
        decision = "Approved" if approval_probability >= 50 else "Rejected"

        # Random Forest comparison (Requirement 5.5)
        rf_approval_probability = 0.0
        if self.rf_model is not None:
            rf_default_prob = float(self.rf_model.predict_proba(features_2d)[0, 1])
            rf_approval_probability = (1 - rf_default_prob) * 100

        return {
            "approval_probability": round(approval_probability, 2),
            "risk_score": round(risk_score, 2),
            "risk_level": risk_level,
            "default_probability": round(xgb_default_prob * 100, 2),
            "decision": decision,
            "rf_approval_probability": round(rf_approval_probability, 2),
        }

    def predict(self, application_data: dict) -> dict:
        """
        Run full prediction pipeline.

        Args:
            application_data: Dict matching LoanApplicationInput fields.

        Returns:
            Dict with:
            - approval_probability (0-100)
            - risk_score (0-100)
            - risk_level (categorical)
            - default_probability (0-100)
            - decision ("Approved" or "Rejected")
            - rf_approval_probability (0-100)
            - timestamp

        Raises:
            RuntimeError: If XGBoost model is not loaded.
            TimeoutError: If inference exceeds 5 seconds.
        """
        if self.xgb_model is None:
            raise RuntimeError("XGBoost model not loaded")

        # Run inference with timeout (Requirement 5.6 / 10.2)
        try:
            future = self._executor.submit(self._run_inference, application_data)
            result = future.result(timeout=INFERENCE_TIMEOUT_SECONDS)
        except FuturesTimeoutError:
            raise TimeoutError(
                f"Prediction inference exceeded {INFERENCE_TIMEOUT_SECONDS}-second timeout"
            )

        result["timestamp"] = datetime.now(timezone.utc).isoformat()
        return result

    def simulate(self, application_data: dict) -> dict:
        """
        Run lightweight simulation (What-If).

        Same inference as predict() but returns only the core metrics.
        No SHAP, no DiCE, no audit logging.

        Args:
            application_data: Dict matching LoanApplicationInput fields.

        Returns:
            Dict with approval_probability, risk_score, risk_level, decision,
            and placeholder loan_readiness_score/readiness_category.

        Raises:
            RuntimeError: If XGBoost model is not loaded.
            TimeoutError: If inference exceeds 5 seconds.
        """
        if self.xgb_model is None:
            raise RuntimeError("XGBoost model not loaded")

        # Run inference with timeout
        try:
            future = self._executor.submit(self._run_inference, application_data)
            result = future.result(timeout=INFERENCE_TIMEOUT_SECONDS)
        except FuturesTimeoutError:
            raise TimeoutError(
                f"Simulation inference exceeded {INFERENCE_TIMEOUT_SECONDS}-second timeout"
            )

        # Compute Loan Readiness Score
        from app.services.readiness_service import get_readiness_service

        try:
            readiness_svc = get_readiness_service()
            readiness_result = readiness_svc.compute(application_data)
            loan_readiness_score = readiness_result["loan_readiness_score"]
            readiness_category = readiness_result["readiness_category"]
        except Exception:
            # Requirement 9.5: graceful fallback if computation fails
            loan_readiness_score = 0.0
            readiness_category = "Fair"

        return {
            "approval_probability": result["approval_probability"],
            "risk_score": result["risk_score"],
            "risk_level": result["risk_level"],
            "decision": result["decision"],
            "loan_readiness_score": loan_readiness_score,
            "readiness_category": readiness_category,
        }


# Singleton instance — initialized when first imported
# Will be properly initialized in FastAPI lifespan handler
prediction_service: PredictionService | None = None


def get_prediction_service() -> PredictionService:
    """Get or create the PredictionService singleton."""
    global prediction_service
    if prediction_service is None:
        prediction_service = PredictionService()
    return prediction_service
