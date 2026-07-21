"""
Reports Router for the AI Loan Decision Platform.

Provides PDF report download for assessments.

Endpoints:
- GET /api/v1/reports/{assessment_id}/pdf — Download PDF report

Requirements: 13.1, 13.2, 13.3, 13.4, 13.5
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response

from app.dependencies import CurrentUser, require_applicant
from app.models.repository import (
    get_application_by_id,
    get_counterfactuals_by_prediction_id,
    get_prediction_by_application_id,
    get_profile_by_user_id,
    get_shap_values_by_prediction_id,
)
from app.services.pdf_service import get_pdf_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


@router.get("/{assessment_id}/pdf")
async def download_pdf_report(
    assessment_id: str,
    current_user: CurrentUser = Depends(require_applicant),
):
    """
    Generate and download a PDF assessment report.

    Requirement 13.1, 13.3.
    """
    # Fetch application
    application = get_application_by_id(assessment_id)
    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    # Access control
    if current_user.role == "Applicant" and application["user_id"] != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    # Fetch prediction
    prediction = get_prediction_by_application_id(assessment_id)
    if not prediction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prediction not found")

    # Fetch SHAP and counterfactuals
    shap_values = get_shap_values_by_prediction_id(prediction["id"])
    counterfactuals = get_counterfactuals_by_prediction_id(prediction["id"])

    # Get applicant name
    profile = get_profile_by_user_id(current_user.id)
    applicant_name = profile["name"] if profile else current_user.email

    # Generate PDF
    try:
        pdf_svc = get_pdf_service()
        pdf_bytes = pdf_svc.generate(
            application=application,
            prediction=prediction,
            shap_values=shap_values,
            counterfactuals=counterfactuals,
            applicant_name=applicant_name,
        )
    except Exception as e:
        logger.error("PDF generation failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate report",
        )

    return Response(
        content=bytes(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=assessment_{assessment_id[:8]}.pdf"},
    )
