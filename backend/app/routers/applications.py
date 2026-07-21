"""
Loan Applications Router for the AI Loan Decision Platform.

Handles loan application submission, retrieval, and review.

Endpoints:
- POST /api/v1/applications — Submit a new loan application (Applicant)
- GET /api/v1/applications — List own applications (Applicant)
- GET /api/v1/applications/review — List all applications (Officer/Admin)
- GET /api/v1/applications/{id} — Get application detail (Applicant/Officer/Admin)

Requirements: 4.2, 4.12, 5.1, 14.2, 14.3, 14.4, 15.2, 15.3
"""

import logging
import math
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.dependencies import CurrentUser, require_applicant, require_officer
from app.models.schemas import (
    LoanApplicationInput,
    PaginatedResponse,
    PredictionResult,
    ShapValue,
    Counterfactual,
)
from app.models.repository import (
    create_application,
    create_counterfactuals,
    create_prediction,
    create_shap_values,
    get_all_applications,
    get_application_by_id,
    get_applications_by_user,
    get_counterfactuals_by_prediction_id,
    get_prediction_by_application_id,
    get_shap_values_by_prediction_id,
    update_application_status,
)
from app.services.audit_service import get_audit_service
from app.services.counterfactual_service import get_counterfactual_service
from app.services.prediction_service import get_prediction_service
from app.services.readiness_service import get_readiness_service
from app.services.shap_service import get_shap_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/applications", tags=["applications"])


@router.post("", response_model=PredictionResult, status_code=status.HTTP_201_CREATED)
async def submit_application(
    request: Request,
    application_input: LoanApplicationInput,
    current_user: CurrentUser = Depends(require_applicant),
):
    """
    Submit a new loan application and receive a credit risk assessment.

    Runs the full prediction pipeline:
    1. Validate input (Pydantic)
    2. Store application in database
    3. Run XGBoost + Random Forest inference
    4. Compute SHAP explanations
    5. Generate counterfactuals (if rejected)
    6. Compute Loan Readiness Score
    7. Persist all outputs
    8. Create audit log entry
    9. Return PredictionResult

    Requirements: 4.2, 4.12, 5.1
    """
    # Convert Pydantic model to dict for services
    app_data = application_input.model_dump()

    # Step 1: Store application in database
    try:
        application = create_application(user_id=current_user.id, data=app_data)
    except Exception as e:
        logger.error("Failed to store application: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to store loan application",
        )

    application_id = application["id"]

    # Step 2: Run prediction pipeline
    try:
        prediction_svc = get_prediction_service()
        prediction_result = prediction_svc.predict(app_data)
    except TimeoutError:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Prediction timed out. Please try again.",
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )

    # Step 3: Compute SHAP explanations
    shap_values_list = None
    top_factors = []
    try:
        shap_svc = get_shap_service()
        shap_values_list = shap_svc.compute_local_shap(app_data)
        if shap_values_list:
            top_factors = shap_svc.get_top_factors(shap_values_list, n=3)
    except Exception as e:
        logger.warning("SHAP computation failed (non-fatal): %s", e)
        # Requirement 7.6: continue without SHAP explanations

    # Step 4: Compute Loan Readiness Score
    try:
        readiness_svc = get_readiness_service()
        readiness_result = readiness_svc.compute(app_data)
        loan_readiness_score = readiness_result["loan_readiness_score"]
        readiness_category = readiness_result["readiness_category"]
    except Exception as e:
        logger.warning("Readiness score computation failed (non-fatal): %s", e)
        loan_readiness_score = 0.0
        readiness_category = "Fair"

    # Step 5: Generate counterfactuals (only for rejected applications)
    counterfactuals_list = None
    if prediction_result["decision"] == "Rejected":
        try:
            cf_svc = get_counterfactual_service()
            counterfactuals_list = cf_svc.generate(app_data, num_cfs=3)
            logger.info("[DEBUG] Counterfactuals generated: %s", 
                       len(counterfactuals_list) if counterfactuals_list else "None")
            if counterfactuals_list:
                logger.info("[DEBUG] First CF: %s", counterfactuals_list[0])
        except Exception as e:
            logger.warning("Counterfactual generation failed (non-fatal): %s", e)
    else:
        logger.info("[DEBUG] Decision is Approved — skipping counterfactuals")

    # Step 6: Persist prediction to database
    prediction_db_data = {
        "application_id": application_id,
        "approval_probability": prediction_result["approval_probability"],
        "risk_score": prediction_result["risk_score"],
        "risk_level": prediction_result["risk_level"],
        "default_probability": prediction_result["default_probability"],
        "decision": prediction_result["decision"],
        "loan_readiness_score": loan_readiness_score,
        "readiness_category": readiness_category,
        "rf_approval_probability": prediction_result["rf_approval_probability"],
    }

    try:
        prediction_record = create_prediction(prediction_db_data)
        prediction_id = prediction_record["id"]
    except Exception as e:
        logger.error("Failed to store prediction: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to store prediction results",
        )

    # Update application status based on decision
    try:
        update_application_status(application_id, prediction_result["decision"])
    except Exception as e:
        logger.warning("Failed to update application status: %s", e)

    # Step 7: Persist SHAP values
    if shap_values_list:
        try:
            shap_db_data = [
                {
                    "feature_name": sv["feature"],
                    "feature_value": sv["value"],
                    "shap_value": sv["shap_value"],
                    "direction": sv["direction"],
                }
                for sv in shap_values_list
            ]
            create_shap_values(prediction_id, shap_db_data)
        except Exception as e:
            logger.warning("Failed to store SHAP values: %s", e)

    # Step 8: Persist counterfactuals
    if counterfactuals_list:
        try:
            cf_db_data = [
                {
                    "feature_name": cf["feature"],
                    "current_value": cf["current_value"],
                    "recommended_value": cf["recommended_value"],
                    "estimated_impact": cf["projected_approval_probability"],
                }
                for cf in counterfactuals_list
            ]
            create_counterfactuals(prediction_id, cf_db_data)
        except Exception as e:
            logger.warning("Failed to store counterfactuals: %s", e)

    # Step 9: Create audit log entry (Requirement 12.1)
    try:
        audit_svc = get_audit_service()
        ip_address = request.client.host if request.client else None
        audit_svc.log_prediction(
            user_id=current_user.id,
            application_id=application_id,
            inputs=app_data,
            outputs=prediction_result,
            shap_values=shap_values_list,
            counterfactuals=counterfactuals_list,
            ip_address=ip_address,
        )
    except Exception as e:
        logger.warning("Audit logging failed (non-fatal): %s", e)

    # Build response
    shap_response = []
    if shap_values_list:
        shap_response = [
            ShapValue(
                feature=sv["feature"],
                value=sv["value"],
                shap_value=sv["shap_value"],
                direction=sv["direction"],
            )
            for sv in shap_values_list
        ]

    top_factors_response = []
    if top_factors:
        top_factors_response = [
            ShapValue(
                feature=tf["feature"],
                value=tf["value"],
                shap_value=tf["shap_value"],
                direction=tf["direction"],
            )
            for tf in top_factors
        ]

    counterfactuals_response = None
    if counterfactuals_list:
        counterfactuals_response = [
            Counterfactual(
                feature=cf["feature"],
                current_value=cf["current_value"],
                recommended_value=cf["recommended_value"],
                projected_approval_probability=cf["projected_approval_probability"],
                projected_risk_score=cf["projected_risk_score"],
                projected_risk_level=cf["projected_risk_level"],
                projected_loan_readiness_score=cf["projected_loan_readiness_score"],
            )
            for cf in counterfactuals_list
        ]

    return PredictionResult(
        application_id=application_id,
        approval_probability=prediction_result["approval_probability"],
        risk_score=prediction_result["risk_score"],
        risk_level=prediction_result["risk_level"],
        default_probability=prediction_result["default_probability"],
        decision=prediction_result["decision"],
        loan_readiness_score=loan_readiness_score,
        readiness_category=readiness_category,
        shap_values=shap_response,
        top_factors=top_factors_response,
        counterfactuals=counterfactuals_response,
        rf_approval_probability=prediction_result["rf_approval_probability"],
        timestamp=datetime.now(timezone.utc),
    )


@router.get("")
async def list_own_applications(
    page: int = Query(1, ge=1),
    current_user: CurrentUser = Depends(require_applicant),
):
    """
    List the current user's loan applications (paginated).

    Sorted by date descending, 20 items per page.

    Requirement 14.2.
    """
    data, total = get_applications_by_user(
        user_id=current_user.id, page=page, page_size=20
    )

    total_pages = max(1, math.ceil(total / 20))

    return {
        "data": data,
        "total": total,
        "page": page,
        "page_size": 20,
        "total_pages": total_pages,
    }


@router.get("/review")
async def list_all_applications_for_review(
    page: int = Query(1, ge=1),
    current_user: CurrentUser = Depends(require_officer),
):
    """
    List all loan applications for officer review (paginated).

    Sorted by submission date descending, 20 items per page.

    Requirement 15.2.
    """
    data, total = get_all_applications(page=page, page_size=20)

    total_pages = max(1, math.ceil(total / 20))

    return {
        "data": data,
        "total": total,
        "page": page,
        "page_size": 20,
        "total_pages": total_pages,
    }


@router.get("/{application_id}")
async def get_application_detail(
    application_id: str,
    current_user: CurrentUser = Depends(require_applicant),
):
    """
    Get full application detail with prediction, SHAP values, and counterfactuals.

    Applicants can only view their own applications.
    Officers/Admins can view any application.

    Requirements: 14.3, 14.4, 15.3.
    """
    # Fetch application
    application = get_application_by_id(application_id)
    if application is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found",
        )

    # Access control: Applicants can only see their own
    if current_user.role == "Applicant" and application["user_id"] != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this application",
        )

    # Fetch prediction
    prediction = get_prediction_by_application_id(application_id)

    # Fetch SHAP values and counterfactuals if prediction exists
    shap_values = []
    counterfactuals = []
    if prediction:
        shap_values = get_shap_values_by_prediction_id(prediction["id"])
        counterfactuals = get_counterfactuals_by_prediction_id(prediction["id"])

    return {
        "application": application,
        "prediction": prediction,
        "shap_values": shap_values,
        "counterfactuals": counterfactuals,
    }
