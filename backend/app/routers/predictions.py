"""
Predictions Router for the AI Loan Decision Platform.

Provides the What-If Simulator endpoint for lightweight predictions
without database persistence or audit logging.

Endpoints:
- POST /api/v1/predictions/simulate — Run What-If simulation

Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.7
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.dependencies import CurrentUser, require_applicant
from app.models.schemas import LoanApplicationInput, SimulationResult
from app.services.prediction_service import get_prediction_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/predictions", tags=["predictions"])


@router.post("/simulate", response_model=SimulationResult)
async def simulate_what_if(
    request: Request,
    application_input: LoanApplicationInput,
    current_user: CurrentUser = Depends(require_applicant),
):
    """
    Run a What-If simulation without persisting results.

    Same inference as predict() but:
    - No SHAP computation
    - No DiCE counterfactuals
    - No database storage
    - No audit logging
    - Target response time < 2 seconds

    Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.7
    """
    app_data = application_input.model_dump()

    try:
        prediction_svc = get_prediction_service()
        result = prediction_svc.simulate(app_data)
    except TimeoutError:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Simulation timed out. Please try again.",
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )

    return SimulationResult(
        approval_probability=result["approval_probability"],
        risk_score=result["risk_score"],
        risk_level=result["risk_level"],
        loan_readiness_score=result["loan_readiness_score"],
        readiness_category=result["readiness_category"],
        decision=result["decision"],
    )
