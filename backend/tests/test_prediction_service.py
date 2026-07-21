"""
Unit tests for PredictionService.

Tests the prediction pipeline including:
- Model loading
- predict() method with XGBoost + Random Forest inference
- simulate() method for What-If scenarios
- Risk level mapping
- Decision threshold logic
- Timeout handling
- Graceful handling of missing models
"""

import numpy as np
import pytest
from unittest.mock import patch, MagicMock
from concurrent.futures import TimeoutError as FuturesTimeoutError

from app.services.prediction_service import (
    PredictionService,
    get_prediction_service,
    map_risk_level,
    INFERENCE_TIMEOUT_SECONDS,
)


# --- Test map_risk_level ---


class TestMapRiskLevel:
    """Tests for the risk level mapping function."""

    def test_very_low_risk_at_zero(self):
        assert map_risk_level(0) == "Very Low Risk"

    def test_very_low_risk_at_boundary(self):
        assert map_risk_level(20) == "Very Low Risk"

    def test_low_risk_just_above_boundary(self):
        assert map_risk_level(20.01) == "Low Risk"

    def test_low_risk_at_boundary(self):
        assert map_risk_level(40) == "Low Risk"

    def test_moderate_risk(self):
        assert map_risk_level(50) == "Moderate Risk"

    def test_moderate_risk_at_boundary(self):
        assert map_risk_level(60) == "Moderate Risk"

    def test_high_risk(self):
        assert map_risk_level(70) == "High Risk"

    def test_high_risk_at_boundary(self):
        assert map_risk_level(80) == "High Risk"

    def test_very_high_risk(self):
        assert map_risk_level(90) == "Very High Risk"

    def test_very_high_risk_at_100(self):
        assert map_risk_level(100) == "Very High Risk"


# --- Test PredictionService ---


def _make_sample_application() -> dict:
    """Create a sample loan application input dict."""
    return {
        "age": 35,
        "monthly_income": 8000.0,
        "employment_status": "Employed",
        "employment_length": 10.0,
        "credit_score": 720,
        "existing_loans": 2,
        "monthly_emi": 1500.0,
        "dti_ratio": 25.0,
        "credit_utilization": 30.0,
        "loan_amount_requested": 50000.0,
    }


class TestPredictionServicePredict:
    """Tests for PredictionService.predict() method."""

    @patch("app.services.prediction_service.ARTIFACTS_DIR")
    def test_predict_returns_expected_keys(self, mock_artifacts_dir, tmp_path):
        """predict() should return all required keys."""
        # Create a mock model that returns probabilities
        mock_xgb = MagicMock()
        mock_xgb.predict_proba.return_value = np.array([[0.7, 0.3]])

        mock_rf = MagicMock()
        mock_rf.predict_proba.return_value = np.array([[0.6, 0.4]])

        service = PredictionService.__new__(PredictionService)
        service.xgb_model = mock_xgb
        service.rf_model = mock_rf
        from concurrent.futures import ThreadPoolExecutor
        service._executor = ThreadPoolExecutor(max_workers=2)

        result = service.predict(_make_sample_application())

        expected_keys = {
            "approval_probability",
            "risk_score",
            "risk_level",
            "default_probability",
            "decision",
            "rf_approval_probability",
            "timestamp",
        }
        assert set(result.keys()) == expected_keys

    @patch("app.services.prediction_service.ARTIFACTS_DIR")
    def test_predict_approval_probability_calculation(self, mock_artifacts_dir):
        """Approval_Probability = (1 - Default_Probability) * 100."""
        mock_xgb = MagicMock()
        # Default probability = 0.3, so approval = 70%
        mock_xgb.predict_proba.return_value = np.array([[0.7, 0.3]])

        mock_rf = MagicMock()
        mock_rf.predict_proba.return_value = np.array([[0.6, 0.4]])

        service = PredictionService.__new__(PredictionService)
        service.xgb_model = mock_xgb
        service.rf_model = mock_rf
        from concurrent.futures import ThreadPoolExecutor
        service._executor = ThreadPoolExecutor(max_workers=2)

        result = service.predict(_make_sample_application())

        assert result["approval_probability"] == 70.0
        assert result["default_probability"] == 30.0
        assert result["risk_score"] == 30.0

    @patch("app.services.prediction_service.ARTIFACTS_DIR")
    def test_predict_decision_approved(self, mock_artifacts_dir):
        """Decision is Approved when approval_probability >= 50."""
        mock_xgb = MagicMock()
        # Default prob = 0.4 → approval = 60% → Approved
        mock_xgb.predict_proba.return_value = np.array([[0.6, 0.4]])

        service = PredictionService.__new__(PredictionService)
        service.xgb_model = mock_xgb
        service.rf_model = None
        from concurrent.futures import ThreadPoolExecutor
        service._executor = ThreadPoolExecutor(max_workers=2)

        result = service.predict(_make_sample_application())

        assert result["decision"] == "Approved"
        assert result["approval_probability"] == 60.0

    @patch("app.services.prediction_service.ARTIFACTS_DIR")
    def test_predict_decision_rejected(self, mock_artifacts_dir):
        """Decision is Rejected when approval_probability < 50."""
        mock_xgb = MagicMock()
        # Default prob = 0.6 → approval = 40% → Rejected
        mock_xgb.predict_proba.return_value = np.array([[0.4, 0.6]])

        service = PredictionService.__new__(PredictionService)
        service.xgb_model = mock_xgb
        service.rf_model = None
        from concurrent.futures import ThreadPoolExecutor
        service._executor = ThreadPoolExecutor(max_workers=2)

        result = service.predict(_make_sample_application())

        assert result["decision"] == "Rejected"
        assert result["approval_probability"] == 40.0

    @patch("app.services.prediction_service.ARTIFACTS_DIR")
    def test_predict_decision_boundary_at_50(self, mock_artifacts_dir):
        """Decision is Approved when approval_probability is exactly 50."""
        mock_xgb = MagicMock()
        # Default prob = 0.5 → approval = 50% → Approved (>= 50)
        mock_xgb.predict_proba.return_value = np.array([[0.5, 0.5]])

        service = PredictionService.__new__(PredictionService)
        service.xgb_model = mock_xgb
        service.rf_model = None
        from concurrent.futures import ThreadPoolExecutor
        service._executor = ThreadPoolExecutor(max_workers=2)

        result = service.predict(_make_sample_application())

        assert result["decision"] == "Approved"
        assert result["approval_probability"] == 50.0

    @patch("app.services.prediction_service.ARTIFACTS_DIR")
    def test_predict_rf_comparison_probability(self, mock_artifacts_dir):
        """Random Forest comparison probability is included."""
        mock_xgb = MagicMock()
        mock_xgb.predict_proba.return_value = np.array([[0.7, 0.3]])

        mock_rf = MagicMock()
        # RF default prob = 0.25 → RF approval = 75%
        mock_rf.predict_proba.return_value = np.array([[0.75, 0.25]])

        service = PredictionService.__new__(PredictionService)
        service.xgb_model = mock_xgb
        service.rf_model = mock_rf
        from concurrent.futures import ThreadPoolExecutor
        service._executor = ThreadPoolExecutor(max_workers=2)

        result = service.predict(_make_sample_application())

        assert result["rf_approval_probability"] == 75.0

    @patch("app.services.prediction_service.ARTIFACTS_DIR")
    def test_predict_rf_unavailable_returns_zero(self, mock_artifacts_dir):
        """When RF model is not loaded, rf_approval_probability is 0."""
        mock_xgb = MagicMock()
        mock_xgb.predict_proba.return_value = np.array([[0.7, 0.3]])

        service = PredictionService.__new__(PredictionService)
        service.xgb_model = mock_xgb
        service.rf_model = None
        from concurrent.futures import ThreadPoolExecutor
        service._executor = ThreadPoolExecutor(max_workers=2)

        result = service.predict(_make_sample_application())

        assert result["rf_approval_probability"] == 0.0

    def test_predict_raises_when_model_not_loaded(self):
        """predict() raises RuntimeError when XGBoost model is None."""
        service = PredictionService.__new__(PredictionService)
        service.xgb_model = None
        service.rf_model = None
        from concurrent.futures import ThreadPoolExecutor
        service._executor = ThreadPoolExecutor(max_workers=2)

        with pytest.raises(RuntimeError, match="XGBoost model not loaded"):
            service.predict(_make_sample_application())

    @patch("app.services.prediction_service.ARTIFACTS_DIR")
    def test_predict_risk_level_mapping(self, mock_artifacts_dir):
        """Risk level is correctly mapped from risk score."""
        mock_xgb = MagicMock()
        # Default prob = 0.15 → risk_score = 15 → Very Low Risk
        mock_xgb.predict_proba.return_value = np.array([[0.85, 0.15]])

        service = PredictionService.__new__(PredictionService)
        service.xgb_model = mock_xgb
        service.rf_model = None
        from concurrent.futures import ThreadPoolExecutor
        service._executor = ThreadPoolExecutor(max_workers=2)

        result = service.predict(_make_sample_application())

        assert result["risk_level"] == "Very Low Risk"
        assert result["risk_score"] == 15.0


class TestPredictionServiceSimulate:
    """Tests for PredictionService.simulate() method."""

    @patch("app.services.prediction_service.ARTIFACTS_DIR")
    def test_simulate_returns_expected_keys(self, mock_artifacts_dir):
        """simulate() should return core metrics only."""
        mock_xgb = MagicMock()
        mock_xgb.predict_proba.return_value = np.array([[0.7, 0.3]])

        service = PredictionService.__new__(PredictionService)
        service.xgb_model = mock_xgb
        service.rf_model = None
        from concurrent.futures import ThreadPoolExecutor
        service._executor = ThreadPoolExecutor(max_workers=2)

        result = service.simulate(_make_sample_application())

        expected_keys = {
            "approval_probability",
            "risk_score",
            "risk_level",
            "decision",
            "loan_readiness_score",
            "readiness_category",
        }
        assert set(result.keys()) == expected_keys

    @patch("app.services.prediction_service.ARTIFACTS_DIR")
    def test_simulate_no_timestamp(self, mock_artifacts_dir):
        """simulate() should NOT include timestamp (no audit)."""
        mock_xgb = MagicMock()
        mock_xgb.predict_proba.return_value = np.array([[0.7, 0.3]])

        service = PredictionService.__new__(PredictionService)
        service.xgb_model = mock_xgb
        service.rf_model = None
        from concurrent.futures import ThreadPoolExecutor
        service._executor = ThreadPoolExecutor(max_workers=2)

        result = service.simulate(_make_sample_application())

        assert "timestamp" not in result

    @patch("app.services.prediction_service.ARTIFACTS_DIR")
    def test_simulate_same_inference_as_predict(self, mock_artifacts_dir):
        """simulate() uses same inference logic as predict()."""
        mock_xgb = MagicMock()
        mock_xgb.predict_proba.return_value = np.array([[0.6, 0.4]])

        service = PredictionService.__new__(PredictionService)
        service.xgb_model = mock_xgb
        service.rf_model = None
        from concurrent.futures import ThreadPoolExecutor
        service._executor = ThreadPoolExecutor(max_workers=2)

        result = service.simulate(_make_sample_application())

        assert result["approval_probability"] == 60.0
        assert result["risk_score"] == 40.0
        assert result["decision"] == "Approved"

    def test_simulate_raises_when_model_not_loaded(self):
        """simulate() raises RuntimeError when XGBoost model is None."""
        service = PredictionService.__new__(PredictionService)
        service.xgb_model = None
        service.rf_model = None
        from concurrent.futures import ThreadPoolExecutor
        service._executor = ThreadPoolExecutor(max_workers=2)

        with pytest.raises(RuntimeError, match="XGBoost model not loaded"):
            service.simulate(_make_sample_application())

    @patch("app.services.prediction_service.ARTIFACTS_DIR")
    def test_simulate_placeholder_readiness(self, mock_artifacts_dir):
        """simulate() returns placeholder readiness values."""
        mock_xgb = MagicMock()
        mock_xgb.predict_proba.return_value = np.array([[0.7, 0.3]])

        service = PredictionService.__new__(PredictionService)
        service.xgb_model = mock_xgb
        service.rf_model = None
        from concurrent.futures import ThreadPoolExecutor
        service._executor = ThreadPoolExecutor(max_workers=2)

        result = service.simulate(_make_sample_application())

        assert result["loan_readiness_score"] == 0.0
        assert result["readiness_category"] == "Fair"


class TestPredictionServiceTimeout:
    """Tests for the 5-second timeout handling."""

    def test_predict_timeout_raises_timeout_error(self):
        """predict() raises TimeoutError when inference exceeds 5 seconds."""
        mock_xgb = MagicMock()

        service = PredictionService.__new__(PredictionService)
        service.xgb_model = mock_xgb
        service.rf_model = None
        from concurrent.futures import ThreadPoolExecutor
        service._executor = ThreadPoolExecutor(max_workers=2)

        # Mock the executor to raise timeout
        with patch.object(service, "_executor") as mock_executor:
            mock_future = MagicMock()
            mock_future.result.side_effect = FuturesTimeoutError()
            mock_executor.submit.return_value = mock_future

            with pytest.raises(TimeoutError, match="5-second timeout"):
                service.predict(_make_sample_application())

    def test_simulate_timeout_raises_timeout_error(self):
        """simulate() raises TimeoutError when inference exceeds 5 seconds."""
        mock_xgb = MagicMock()

        service = PredictionService.__new__(PredictionService)
        service.xgb_model = mock_xgb
        service.rf_model = None
        from concurrent.futures import ThreadPoolExecutor
        service._executor = ThreadPoolExecutor(max_workers=2)

        # Mock the executor to raise timeout
        with patch.object(service, "_executor") as mock_executor:
            mock_future = MagicMock()
            mock_future.result.side_effect = FuturesTimeoutError()
            mock_executor.submit.return_value = mock_future

            with pytest.raises(TimeoutError, match="5-second timeout"):
                service.simulate(_make_sample_application())


class TestGetPredictionService:
    """Tests for the singleton factory function."""

    def test_get_prediction_service_returns_instance(self):
        """get_prediction_service() returns a PredictionService instance."""
        import app.services.prediction_service as module

        # Reset singleton
        module.prediction_service = None

        service = get_prediction_service()
        assert isinstance(service, PredictionService)

    def test_get_prediction_service_returns_same_instance(self):
        """get_prediction_service() returns the same singleton."""
        import app.services.prediction_service as module

        # Reset singleton
        module.prediction_service = None

        service1 = get_prediction_service()
        service2 = get_prediction_service()
        assert service1 is service2


class TestPredictionServiceIntegration:
    """Integration tests using the actual trained models (if available)."""

    def test_predict_with_real_models(self):
        """Test predict() with actual trained models from artifacts."""
        from app.services.prediction_service import ARTIFACTS_DIR

        xgb_path = ARTIFACTS_DIR / "xgboost_model.joblib"
        if not xgb_path.exists():
            pytest.skip("XGBoost model not available — run training first")

        import app.services.prediction_service as module
        module.prediction_service = None

        service = get_prediction_service()
        result = service.predict(_make_sample_application())

        # Verify all values are in valid ranges
        assert 0 <= result["approval_probability"] <= 100
        assert 0 <= result["risk_score"] <= 100
        assert 0 <= result["default_probability"] <= 100
        assert 0 <= result["rf_approval_probability"] <= 100
        assert result["risk_level"] in [
            "Very Low Risk", "Low Risk", "Moderate Risk", "High Risk", "Very High Risk"
        ]
        assert result["decision"] in ["Approved", "Rejected"]
        assert "timestamp" in result

        # Verify mathematical relationships
        assert abs(result["approval_probability"] + result["default_probability"] - 100) < 0.1
        assert abs(result["risk_score"] - result["default_probability"]) < 0.1

    def test_simulate_with_real_models(self):
        """Test simulate() with actual trained models from artifacts."""
        from app.services.prediction_service import ARTIFACTS_DIR

        xgb_path = ARTIFACTS_DIR / "xgboost_model.joblib"
        if not xgb_path.exists():
            pytest.skip("XGBoost model not available — run training first")

        import app.services.prediction_service as module
        module.prediction_service = None

        service = get_prediction_service()
        result = service.simulate(_make_sample_application())

        assert 0 <= result["approval_probability"] <= 100
        assert 0 <= result["risk_score"] <= 100
        assert result["risk_level"] in [
            "Very Low Risk", "Low Risk", "Moderate Risk", "High Risk", "Very High Risk"
        ]
        assert result["decision"] in ["Approved", "Rejected"]
