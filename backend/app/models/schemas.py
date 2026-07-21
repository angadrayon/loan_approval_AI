"""
Pydantic request/response schemas for the AI Loan Decision Support Platform.

This module defines all data validation models used across the API endpoints,
including loan application input, prediction results, simulation results,
SHAP explanations, counterfactual recommendations, fairness metrics,
audit logging, and error responses.

All field constraints match the validation rules defined in Requirement 4.
Uses Pydantic v2 syntax (BaseModel, Field, model_validator).
"""

from datetime import datetime
from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, Field, model_validator


# ============================================================
# Loan Application Input
# ============================================================


class LoanApplicationInput(BaseModel):
    """Input schema for loan application submission.

    Collects all financial information required for credit risk assessment.
    All field constraints enforce the validation rules from Requirement 4.
    """

    age: int = Field(ge=18, le=100, description="Applicant age in years")
    monthly_income: float = Field(
        gt=0, le=10_000_000, description="Monthly income in currency units"
    )
    employment_status: Literal["Employed", "Self-Employed", "Unemployed", "Retired"] = (
        Field(description="Current employment status")
    )
    employment_length: float = Field(
        ge=0, le=50, description="Years of employment"
    )
    credit_score: int = Field(
        ge=300, le=850, description="Credit score (FICO range)"
    )
    existing_loans: int = Field(
        ge=0, le=50, description="Number of existing active loans"
    )
    monthly_emi: float = Field(
        ge=0, description="Current monthly EMI payments"
    )
    dti_ratio: float = Field(
        ge=0, le=100, description="Debt-to-Income ratio as percentage"
    )
    credit_utilization: float = Field(
        ge=0, le=100, description="Credit utilization as percentage"
    )
    loan_amount_requested: float = Field(
        gt=0, le=10_000_000, description="Requested loan amount"
    )

    @model_validator(mode="after")
    def emi_not_exceeding_income(self):
        """Validate that monthly EMI does not exceed monthly income."""
        if self.monthly_emi > self.monthly_income:
            raise ValueError("Monthly EMI cannot exceed Monthly Income")
        return self


# ============================================================
# SHAP Value
# ============================================================


class ShapValue(BaseModel):
    """Represents a single SHAP value for a feature in a prediction.

    SHAP values explain the contribution of each feature toward the
    model's prediction, indicating both magnitude and direction.
    """

    feature: str = Field(description="Feature name")
    value: float = Field(description="The input feature value")
    shap_value: float = Field(description="SHAP contribution value")
    direction: Literal["positive", "negative"] = Field(
        description="Direction of contribution toward approval"
    )


# ============================================================
# Counterfactual
# ============================================================


class Counterfactual(BaseModel):
    """Represents a counterfactual explanation for a rejected application.

    Shows the minimum change required for a single feature to move
    the prediction toward approval, along with projected outcomes.
    """

    feature: str = Field(description="Feature name to change")
    current_value: float = Field(description="Current feature value")
    recommended_value: float = Field(description="Recommended target value")
    projected_approval_probability: float = Field(
        description="Projected approval probability after change"
    )
    projected_risk_score: float = Field(
        description="Projected risk score after change"
    )
    projected_risk_level: Literal[
        "Very Low Risk", "Low Risk", "Moderate Risk", "High Risk", "Very High Risk"
    ] = Field(description="Projected risk level after change")
    projected_loan_readiness_score: float = Field(
        description="Projected loan readiness score after change"
    )


# ============================================================
# Prediction Result
# ============================================================


class PredictionResult(BaseModel):
    """Complete prediction result returned after loan application assessment.

    Includes approval decision, risk metrics, SHAP explanations,
    counterfactual recommendations (for rejected applications), and
    the Random Forest comparison probability.
    """

    application_id: str = Field(description="Unique application identifier")
    approval_probability: float = Field(
        ge=0, le=100, description="Approval probability percentage"
    )
    risk_score: float = Field(
        ge=0, le=100, description="Risk score (0=Very Low, 100=Very High)"
    )
    risk_level: Literal[
        "Very Low Risk", "Low Risk", "Moderate Risk", "High Risk", "Very High Risk"
    ] = Field(description="Categorical risk level")
    default_probability: float = Field(
        ge=0, le=100, description="Default probability percentage"
    )
    decision: Literal["Approved", "Rejected"] = Field(
        description="Final loan decision"
    )
    loan_readiness_score: float = Field(
        ge=0, le=100, description="Loan readiness score (0-100)"
    )
    readiness_category: Literal["Poor", "Fair", "Good", "Excellent"] = Field(
        description="Readiness category based on score"
    )
    shap_values: list[ShapValue] = Field(
        description="SHAP values for all input features"
    )
    top_factors: list[ShapValue] = Field(
        description="Top 3 factors by absolute SHAP magnitude"
    )
    counterfactuals: list[Counterfactual] | None = Field(
        default=None,
        description="Counterfactual recommendations (only for Rejected decisions)",
    )
    rf_approval_probability: float = Field(
        ge=0, le=100, description="Random Forest approval probability for comparison"
    )
    timestamp: datetime = Field(description="Prediction timestamp")


# ============================================================
# Simulation Result (What-If)
# ============================================================


class SimulationResult(BaseModel):
    """Result from the What-If Simulator.

    A lightweight prediction result without SHAP values or counterfactuals,
    designed for fast interactive simulation without audit logging.
    """

    approval_probability: float = Field(
        ge=0, le=100, description="Simulated approval probability percentage"
    )
    risk_score: float = Field(
        ge=0, le=100, description="Simulated risk score"
    )
    risk_level: Literal[
        "Very Low Risk", "Low Risk", "Moderate Risk", "High Risk", "Very High Risk"
    ] = Field(description="Simulated risk level")
    loan_readiness_score: float = Field(
        ge=0, le=100, description="Simulated loan readiness score"
    )
    readiness_category: Literal["Poor", "Fair", "Good", "Excellent"] = Field(
        description="Simulated readiness category"
    )
    decision: Literal["Approved", "Rejected"] = Field(
        description="Simulated loan decision"
    )


# ============================================================
# Fairness Metrics
# ============================================================


class FairnessMetrics(BaseModel):
    """Fairness monitoring metrics computed using Fairlearn.

    Tracks Demographic Parity and Equalized Odds differences,
    proxy bias correlations, and data sufficiency indicators.
    """

    demographic_parity_diff: float = Field(
        description="Demographic Parity difference metric"
    )
    equalized_odds_diff: float = Field(
        description="Equalized Odds difference metric"
    )
    proxy_correlations: dict[str, float] = Field(
        description="Pearson correlations between protected attributes and features"
    )
    prediction_count: int = Field(
        description="Number of predictions used for metric computation"
    )
    computed_at: datetime = Field(
        description="Timestamp when metrics were computed"
    )
    insufficient_data: bool = Field(
        default=False,
        description="True if fewer than 30 predictions exist for reliable metrics",
    )


# ============================================================
# Audit Types
# ============================================================


class AuditLog(BaseModel):
    """Represents a single audit log entry.

    Records user actions, prediction events, and authentication events
    for regulatory compliance and decision traceability.
    """

    id: str = Field(description="Unique audit log identifier")
    user_id: str | None = Field(
        default=None, description="User who triggered the event"
    )
    event_type: str = Field(description="Type of audited event")
    event_data: dict = Field(description="Event payload data")
    ip_address: str | None = Field(
        default=None, description="IP address of the request"
    )
    created_at: datetime = Field(description="Timestamp of the event")


class AuditFilters(BaseModel):
    """Filters for querying audit logs.

    Supports filtering by date range, user, and decision outcome.
    """

    date_from: str | None = Field(
        default=None, description="Start date filter (ISO format)"
    )
    date_to: str | None = Field(
        default=None, description="End date filter (ISO format)"
    )
    user_id: str | None = Field(
        default=None, description="Filter by specific user ID"
    )
    decision: Literal["Approved", "Rejected"] | None = Field(
        default=None, description="Filter by loan decision outcome"
    )


# ============================================================
# Pagination
# ============================================================

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response wrapper.

    Wraps any list of items with pagination metadata including
    total count, current page, page size, and total pages.
    """

    data: list[T] = Field(description="List of items for the current page")
    total: int = Field(description="Total number of items across all pages")
    page: int = Field(description="Current page number")
    page_size: int = Field(description="Number of items per page")
    total_pages: int = Field(description="Total number of pages")


# ============================================================
# Model Statistics
# ============================================================


class ModelMetrics(BaseModel):
    """Performance metrics for a single ML model.

    Includes AUC-ROC, F1 Score, and KS Statistic computed on
    the test dataset.
    """

    auc_roc: float = Field(description="Area Under ROC Curve")
    f1_score: float = Field(description="F1 Score")
    ks_statistic: float = Field(description="Kolmogorov-Smirnov Statistic")


class ModelStatistics(BaseModel):
    """Side-by-side performance comparison of XGBoost and Random Forest models."""

    xgboost: ModelMetrics = Field(description="XGBoost model metrics")
    random_forest: ModelMetrics = Field(description="Random Forest model metrics")


# ============================================================
# User / Profile
# ============================================================


class UserProfile(BaseModel):
    """User profile information including role assignment."""

    id: str = Field(description="Profile record ID")
    user_id: str = Field(description="Supabase Auth user ID")
    name: str = Field(description="User display name")
    email: str = Field(description="User email address")
    role: Literal["Applicant", "Bank_Officer", "Admin"] = Field(
        description="Assigned platform role"
    )
    created_at: datetime = Field(description="Account creation timestamp")


class UserRoleUpdate(BaseModel):
    """Request schema for updating a user's role."""

    role: Literal["Applicant", "Bank_Officer", "Admin"] = Field(
        description="New role to assign"
    )


# ============================================================
# Auth Schemas
# ============================================================


class RegisterRequest(BaseModel):
    """Request schema for user registration."""

    name: str = Field(
        min_length=1, max_length=100, description="User display name"
    )
    email: str = Field(description="User email address")
    password: str = Field(
        min_length=8, max_length=128, description="Account password"
    )


class LoginRequest(BaseModel):
    """Request schema for user login."""

    email: str = Field(description="User email address")
    password: str = Field(description="Account password")


class AuthResponse(BaseModel):
    """Response schema for successful authentication.

    Returns access and refresh tokens along with the user profile.
    """

    access_token: str = Field(description="JWT access token")
    refresh_token: str = Field(description="JWT refresh token")
    user: UserProfile = Field(description="Authenticated user profile")


# ============================================================
# Error Response Models
# ============================================================


class ErrorDetail(BaseModel):
    """Individual error detail for validation or field-level errors."""

    field: str | None = Field(
        default=None, description="Field name that caused the error"
    )
    message: str = Field(description="Human-readable error message")


class ErrorResponse(BaseModel):
    """Standard error response returned by the API."""

    detail: str = Field(description="High-level error description")
    errors: list[ErrorDetail] | None = Field(
        default=None, description="List of specific error details"
    )


class ValidationErrorResponse(BaseModel):
    """Validation error response with field-level error details."""

    detail: str = Field(
        default="Validation error", description="Error summary"
    )
    errors: list[ErrorDetail] = Field(
        description="List of validation errors by field"
    )
