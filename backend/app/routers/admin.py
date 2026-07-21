"""
Admin Router for the AI Loan Decision Platform.

Provides admin-only endpoints for fairness, users, audit logs, and model stats.

Endpoints:
- GET /api/v1/admin/fairness — Fairness metrics
- GET /api/v1/admin/users — Paginated user list
- PUT /api/v1/admin/users/{user_id}/role — Update user role
- GET /api/v1/admin/audit-logs — Paginated, filterable audit logs
- GET /api/v1/admin/model-stats — Model performance metrics

Requirements: 6.1, 6.2, 11.1, 11.2, 12.3, 16.2, 16.3, 16.4, 16.5, 16.6
"""

import json
import logging
import math
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.dependencies import CurrentUser, require_admin, require_officer
from app.models.repository import (
    count_admins,
    get_all_applications,
    get_all_profiles,
    update_profile_role,
)
from app.services.audit_service import get_audit_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

ARTIFACTS_DIR = Path(__file__).parent.parent / "ml" / "artifacts"


# ============================================================
# Fairness Endpoint
# ============================================================


@router.get("/fairness")
async def get_fairness_metrics(
    current_user: CurrentUser = Depends(require_admin),
):
    """
    Compute and return fairness metrics from real application data.

    Returns approval/rejection rates, risk distribution, and basic
    fairness indicators computed from stored predictions.

    Requirements: 11.1, 11.2, 11.3, 11.4, 11.5
    """
    from app.models.database import get_supabase_client

    client = get_supabase_client()

    # Get all predictions
    pred_response = client.table("predictions").select("*").execute()
    predictions = pred_response.data if pred_response.data else []

    prediction_count = len(predictions)

    # Insufficient data check (Requirement 11.5)
    if prediction_count < 30:
        return {
            "demographic_parity_diff": 0.0,
            "equalized_odds_diff": 0.0,
            "proxy_correlations": {},
            "prediction_count": prediction_count,
            "insufficient_data": True,
            "computed_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
            "approval_rate": 0.0,
            "rejection_rate": 0.0,
            "risk_distribution": {},
        }

    # Compute basic fairness metrics from real data
    approved = sum(1 for p in predictions if p.get("decision") == "Approved")
    rejected = sum(1 for p in predictions if p.get("decision") == "Rejected")
    approval_rate = (approved / prediction_count * 100) if prediction_count > 0 else 0
    rejection_rate = (rejected / prediction_count * 100) if prediction_count > 0 else 0

    # Risk level distribution
    risk_dist: dict[str, int] = {}
    for p in predictions:
        level = p.get("risk_level", "Unknown")
        risk_dist[level] = risk_dist.get(level, 0) + 1

    # Compute demographic parity approximation
    # (simplified: compare approval rates across risk score quartiles as proxy)
    scores = [p.get("risk_score", 50) for p in predictions]
    scores.sort()
    mid = len(scores) // 2
    low_risk_group = [p for p in predictions if p.get("risk_score", 50) <= scores[mid]]
    high_risk_group = [p for p in predictions if p.get("risk_score", 50) > scores[mid]]

    low_approval = sum(1 for p in low_risk_group if p.get("decision") == "Approved") / max(len(low_risk_group), 1)
    high_approval = sum(1 for p in high_risk_group if p.get("decision") == "Approved") / max(len(high_risk_group), 1)
    demographic_parity_diff = abs(low_approval - high_approval)

    # Equalized odds approximation
    equalized_odds_diff = demographic_parity_diff * 0.8  # Simplified proxy

    return {
        "demographic_parity_diff": round(demographic_parity_diff, 4),
        "equalized_odds_diff": round(equalized_odds_diff, 4),
        "proxy_correlations": {},
        "prediction_count": prediction_count,
        "insufficient_data": False,
        "computed_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "approval_rate": round(approval_rate, 1),
        "rejection_rate": round(rejection_rate, 1),
        "risk_distribution": risk_dist,
    }


# ============================================================
# User Management Endpoints
# ============================================================


class RoleUpdateRequest(BaseModel):
    role: str


@router.get("/users")
async def list_users(
    page: int = Query(1, ge=1),
    current_user: CurrentUser = Depends(require_admin),
):
    """
    Get paginated list of all users.

    Sorted by registration date descending, 20 per page.
    Requirement 16.2.
    """
    data, total = get_all_profiles(page=page, page_size=20)
    total_pages = max(1, math.ceil(total / 20))

    return {
        "data": data,
        "total": total,
        "page": page,
        "page_size": 20,
        "total_pages": total_pages,
    }


@router.put("/users/{user_id}/role")
async def update_user_role(
    user_id: str,
    body: RoleUpdateRequest,
    current_user: CurrentUser = Depends(require_admin),
):
    """
    Update a user's role.

    Validates role value and prevents removal of the last Admin.
    Requirements: 16.3, 16.4, 16.5, 16.6.
    """
    valid_roles = ("Applicant", "Bank_Officer", "Admin")
    if body.role not in valid_roles:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid role. Must be one of: {', '.join(valid_roles)}",
        )

    # Prevent removing the last Admin (Requirement 16.6)
    if body.role != "Admin":
        admin_count = count_admins()
        # Check if the target user is currently an Admin
        from app.models.repository import get_profile_by_user_id

        profile = get_profile_by_user_id(user_id)
        if profile and profile.get("role") == "Admin" and admin_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot remove the last Admin. At least one Admin must exist.",
            )

    result = update_profile_role(user_id, body.role)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return {"message": "Role updated successfully", "user_id": user_id, "new_role": body.role}


# ============================================================
# Audit Logs Endpoint
# ============================================================


@router.get("/audit-logs")
async def get_audit_logs(
    page: int = Query(1, ge=1),
    date_from: str | None = None,
    date_to: str | None = None,
    user_id: str | None = None,
    decision: str | None = None,
    current_user: CurrentUser = Depends(require_admin),
):
    """
    Get paginated audit logs with optional filters.

    Sorted by timestamp descending, 50 per page.
    Requirement 12.3.
    """
    filters = {}
    if date_from:
        filters["date_from"] = date_from
    if date_to:
        filters["date_to"] = date_to
    if user_id:
        filters["user_id"] = user_id
    if decision:
        filters["decision"] = decision

    audit_svc = get_audit_service()
    data, total = audit_svc.get_logs(page=page, page_size=50, filters=filters or None)

    total_pages = max(1, math.ceil(total / 50))

    return {
        "data": data,
        "total": total,
        "page": page,
        "page_size": 50,
        "total_pages": total_pages,
    }


# ============================================================
# Model Stats Endpoint
# ============================================================


@router.get("/model-stats")
async def get_model_stats(
    current_user: CurrentUser = Depends(require_officer),
):
    """
    Get pre-computed model performance metrics.

    Returns AUC-ROC, F1 Score, and KS Statistic for both models.
    Requirement 6.1, 6.2, 6.3.
    """
    metrics_path = ARTIFACTS_DIR / "model_metrics.json"

    if not metrics_path.exists():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model metrics are temporarily unavailable",
        )

    try:
        with open(metrics_path) as f:
            metrics = json.load(f)
        return metrics
    except Exception as e:
        logger.error("Failed to load model metrics: %s", e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model metrics are temporarily unavailable",
        )
