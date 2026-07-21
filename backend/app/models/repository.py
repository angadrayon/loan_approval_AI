"""
Repository layer for CRUD operations on all database tables.

All functions use the service role Supabase client (bypasses RLS) for
unrestricted backend access. Pagination helpers use Supabase's .range()
method for offset-based pagination.

Default page sizes:
- Applications: 20 per page
- Users/Profiles: 20 per page
- Audit logs: 50 per page
"""

from __future__ import annotations

import logging
from typing import Any

from app.models.database import get_supabase_client

logger = logging.getLogger(__name__)

# Default page sizes
DEFAULT_PAGE_SIZE_APPLICATIONS = 20
DEFAULT_PAGE_SIZE_PROFILES = 20
DEFAULT_PAGE_SIZE_AUDIT_LOGS = 50


# ============================================================
# Pagination Helper
# ============================================================


def paginate(
    table: str,
    query_builder,
    page: int,
    page_size: int,
) -> tuple[list[dict], int]:
    """Apply pagination to a Supabase query and return (data, total_count).

    Uses Supabase's .range(start, end) for offset/limit pagination.
    Executes a separate count query to determine total items.

    Args:
        table: Table name for the count query.
        query_builder: A Supabase query builder with filters already applied.
        page: Page number (1-indexed).
        page_size: Number of items per page.

    Returns:
        Tuple of (list of row dicts, total count).
    """
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 1

    start = (page - 1) * page_size
    end = start + page_size - 1

    # Execute the paginated data query
    response = query_builder.range(start, end).execute()
    data = response.data if response.data else []

    # Execute a count query for the same table
    client = get_supabase_client()
    count_response = client.table(table).select("*", count="exact").execute()
    total = count_response.count if count_response.count is not None else 0

    return data, total


def _paginate_with_filters(
    table: str,
    filters: dict[str, Any] | None,
    page: int,
    page_size: int,
    order_column: str = "created_at",
    order_desc: bool = True,
) -> tuple[list[dict], int]:
    """Internal helper that builds a filtered, paginated query.

    Args:
        table: Table name.
        filters: Dict of column -> value equality filters.
        page: Page number (1-indexed).
        page_size: Items per page.
        order_column: Column to sort by.
        order_desc: Whether to sort descending.

    Returns:
        Tuple of (list of row dicts, total count).
    """
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 1

    start = (page - 1) * page_size
    end = start + page_size - 1

    client = get_supabase_client()

    # Build data query
    data_query = client.table(table).select("*")
    count_query = client.table(table).select("*", count="exact")

    if filters:
        for column, value in filters.items():
            data_query = data_query.eq(column, value)
            count_query = count_query.eq(column, value)

    data_query = data_query.order(order_column, desc=order_desc)
    response = data_query.range(start, end).execute()
    data = response.data if response.data else []

    count_response = count_query.execute()
    total = count_response.count if count_response.count is not None else 0

    return data, total


# ============================================================
# Profiles
# ============================================================


def get_profile_by_user_id(user_id: str) -> dict | None:
    """Fetch a profile by its associated auth user ID.

    Returns None if no profile is found.
    """
    try:
        client = get_supabase_client()
        response = (
            client.table("profiles")
            .select("*")
            .eq("user_id", user_id)
            .single()
            .execute()
        )
        return response.data
    except Exception as e:
        logger.warning("Profile not found for user_id=%s: %s", user_id, e)
        return None


def get_all_profiles(
    page: int = 1, page_size: int = DEFAULT_PAGE_SIZE_PROFILES
) -> tuple[list[dict], int]:
    """Fetch all profiles with pagination, sorted by created_at DESC.

    Returns:
        Tuple of (list of profile dicts, total count).
    """
    return _paginate_with_filters(
        table="profiles",
        filters=None,
        page=page,
        page_size=page_size,
        order_column="created_at",
        order_desc=True,
    )


def update_profile_role(user_id: str, new_role: str) -> dict | None:
    """Update a user's role in their profile.

    Args:
        user_id: The auth user ID.
        new_role: The new role ('Applicant', 'Bank_Officer', or 'Admin').

    Returns:
        Updated profile dict, or None if not found.
    """
    try:
        client = get_supabase_client()
        response = (
            client.table("profiles")
            .update({"role": new_role})
            .eq("user_id", user_id)
            .execute()
        )
        if response.data:
            return response.data[0]
        return None
    except Exception as e:
        logger.error("Failed to update role for user_id=%s: %s", user_id, e)
        return None


def count_admins() -> int:
    """Count the number of users with the Admin role.

    Used to prevent removal of the last admin.
    """
    try:
        client = get_supabase_client()
        response = (
            client.table("profiles")
            .select("*", count="exact")
            .eq("role", "Admin")
            .execute()
        )
        return response.count if response.count is not None else 0
    except Exception as e:
        logger.error("Failed to count admins: %s", e)
        return 0


# ============================================================
# Loan Applications
# ============================================================


def create_application(user_id: str, data: dict) -> dict:
    """Create a new loan application.

    Args:
        user_id: The applicant's auth user ID.
        data: Dict of application fields (age, monthly_income, etc.).

    Returns:
        The created application record.
    """
    client = get_supabase_client()
    payload = {**data, "user_id": user_id}
    response = client.table("loan_applications").insert(payload).execute()
    return response.data[0]


def get_application_by_id(application_id: str) -> dict | None:
    """Fetch a single loan application by its ID.

    Returns None if not found.
    """
    try:
        client = get_supabase_client()
        response = (
            client.table("loan_applications")
            .select("*")
            .eq("id", application_id)
            .single()
            .execute()
        )
        return response.data
    except Exception as e:
        logger.warning("Application not found id=%s: %s", application_id, e)
        return None


def get_applications_by_user(
    user_id: str, page: int = 1, page_size: int = DEFAULT_PAGE_SIZE_APPLICATIONS
) -> tuple[list[dict], int]:
    """Fetch loan applications for a specific user, paginated.

    Sorted by created_at DESC.

    Returns:
        Tuple of (list of application dicts, total count for this user).
    """
    if page < 1:
        page = 1

    start = (page - 1) * page_size
    end = start + page_size - 1

    client = get_supabase_client()

    data_query = (
        client.table("loan_applications")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
    )
    response = data_query.range(start, end).execute()
    data = response.data if response.data else []

    count_response = (
        client.table("loan_applications")
        .select("*", count="exact")
        .eq("user_id", user_id)
        .execute()
    )
    total = count_response.count if count_response.count is not None else 0

    return data, total


def get_all_applications(
    page: int = 1, page_size: int = DEFAULT_PAGE_SIZE_APPLICATIONS
) -> tuple[list[dict], int]:
    """Fetch all loan applications with pagination (for officers/admins).

    Sorted by created_at DESC.

    Returns:
        Tuple of (list of application dicts, total count).
    """
    return _paginate_with_filters(
        table="loan_applications",
        filters=None,
        page=page,
        page_size=page_size,
        order_column="created_at",
        order_desc=True,
    )


def update_application_status(application_id: str, status: str) -> dict | None:
    """Update the status of a loan application.

    Args:
        application_id: The application UUID.
        status: New status ('Pending Review', 'Approved', or 'Rejected').

    Returns:
        Updated application dict, or None if not found.
    """
    try:
        client = get_supabase_client()
        response = (
            client.table("loan_applications")
            .update({"status": status})
            .eq("id", application_id)
            .execute()
        )
        if response.data:
            return response.data[0]
        return None
    except Exception as e:
        logger.error(
            "Failed to update application status id=%s: %s", application_id, e
        )
        return None


# ============================================================
# Predictions
# ============================================================


def create_prediction(data: dict) -> dict:
    """Store a prediction result in the database.

    Args:
        data: Dict containing all prediction fields
              (application_id, approval_probability, risk_score, etc.).

    Returns:
        The created prediction record.
    """
    client = get_supabase_client()
    response = client.table("predictions").insert(data).execute()
    return response.data[0]


def get_prediction_by_application_id(application_id: str) -> dict | None:
    """Fetch the prediction associated with a loan application.

    Returns None if no prediction exists for the given application.
    """
    try:
        client = get_supabase_client()
        response = (
            client.table("predictions")
            .select("*")
            .eq("application_id", application_id)
            .single()
            .execute()
        )
        return response.data
    except Exception as e:
        logger.warning(
            "Prediction not found for application_id=%s: %s", application_id, e
        )
        return None


# ============================================================
# SHAP Values
# ============================================================


def create_shap_values(prediction_id: str, shap_values: list[dict]) -> list[dict]:
    """Bulk-insert SHAP values for a prediction.

    Args:
        prediction_id: The prediction UUID.
        shap_values: List of dicts with feature_name, feature_value,
                     shap_value, and direction.

    Returns:
        List of created SHAP value records.
    """
    client = get_supabase_client()
    rows = [{"prediction_id": prediction_id, **sv} for sv in shap_values]
    response = client.table("shap_values").insert(rows).execute()
    return response.data if response.data else []


def get_shap_values_by_prediction_id(prediction_id: str) -> list[dict]:
    """Fetch all SHAP values for a given prediction.

    Returns an empty list if none are found.
    """
    try:
        client = get_supabase_client()
        response = (
            client.table("shap_values")
            .select("*")
            .eq("prediction_id", prediction_id)
            .execute()
        )
        return response.data if response.data else []
    except Exception as e:
        logger.warning(
            "SHAP values not found for prediction_id=%s: %s", prediction_id, e
        )
        return []


# ============================================================
# Counterfactuals
# ============================================================


def create_counterfactuals(
    prediction_id: str, counterfactuals: list[dict]
) -> list[dict]:
    """Bulk-insert counterfactual explanations for a prediction.

    Args:
        prediction_id: The prediction UUID.
        counterfactuals: List of dicts with feature_name, current_value,
                         recommended_value, and estimated_impact.

    Returns:
        List of created counterfactual records.
    """
    client = get_supabase_client()
    rows = [{"prediction_id": prediction_id, **cf} for cf in counterfactuals]
    response = client.table("counterfactuals").insert(rows).execute()
    return response.data if response.data else []


def get_counterfactuals_by_prediction_id(prediction_id: str) -> list[dict]:
    """Fetch all counterfactual explanations for a given prediction.

    Returns an empty list if none are found.
    """
    try:
        client = get_supabase_client()
        response = (
            client.table("counterfactuals")
            .select("*")
            .eq("prediction_id", prediction_id)
            .execute()
        )
        return response.data if response.data else []
    except Exception as e:
        logger.warning(
            "Counterfactuals not found for prediction_id=%s: %s", prediction_id, e
        )
        return []


# ============================================================
# Audit Logs
# ============================================================


def create_audit_log(data: dict) -> dict:
    """Create an immutable audit log entry.

    Args:
        data: Dict with event_type, event_data, and optionally
              user_id and ip_address.

    Returns:
        The created audit log record.
    """
    client = get_supabase_client()
    response = client.table("audit_logs").insert(data).execute()
    return response.data[0]


def get_audit_logs(
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE_AUDIT_LOGS,
    filters: dict | None = None,
) -> tuple[list[dict], int]:
    """Fetch audit logs with pagination and optional filters.

    Sorted by created_at DESC. Supports filtering by:
    - date_from: ISO date string (created_at >= date_from)
    - date_to: ISO date string (created_at <= date_to)
    - user_id: Filter by specific user
    - decision: Filter by decision in event_data JSONB

    Args:
        page: Page number (1-indexed).
        page_size: Items per page (default 50).
        filters: Optional dict of filter criteria.

    Returns:
        Tuple of (list of audit log dicts, total count matching filters).
    """
    if page < 1:
        page = 1

    start = (page - 1) * page_size
    end = start + page_size - 1

    client = get_supabase_client()

    data_query = client.table("audit_logs").select("*")
    count_query = client.table("audit_logs").select("*", count="exact")

    if filters:
        if filters.get("date_from"):
            data_query = data_query.gte("created_at", filters["date_from"])
            count_query = count_query.gte("created_at", filters["date_from"])

        if filters.get("date_to"):
            data_query = data_query.lte("created_at", filters["date_to"])
            count_query = count_query.lte("created_at", filters["date_to"])

        if filters.get("user_id"):
            data_query = data_query.eq("user_id", filters["user_id"])
            count_query = count_query.eq("user_id", filters["user_id"])

        if filters.get("decision"):
            # Filter by decision stored inside the event_data JSONB column
            data_query = data_query.eq(
                "event_data->>decision", filters["decision"]
            )
            count_query = count_query.eq(
                "event_data->>decision", filters["decision"]
            )

    data_query = data_query.order("created_at", desc=True)
    response = data_query.range(start, end).execute()
    data = response.data if response.data else []

    count_response = count_query.execute()
    total = count_response.count if count_response.count is not None else 0

    return data, total


# ============================================================
# Fairness Metrics
# ============================================================


def create_fairness_metrics(data: dict) -> dict:
    """Store a new fairness metrics snapshot.

    Args:
        data: Dict with demographic_parity_diff, equalized_odds_diff,
              proxy_correlations, and prediction_count.

    Returns:
        The created fairness metrics record.
    """
    client = get_supabase_client()
    response = client.table("fairness_metrics").insert(data).execute()
    return response.data[0]


def get_latest_fairness_metrics() -> dict | None:
    """Fetch the most recently computed fairness metrics.

    Returns None if no metrics have been computed yet.
    """
    try:
        client = get_supabase_client()
        response = (
            client.table("fairness_metrics")
            .select("*")
            .order("computed_at", desc=True)
            .limit(1)
            .execute()
        )
        if response.data:
            return response.data[0]
        return None
    except Exception as e:
        logger.warning("Failed to fetch latest fairness metrics: %s", e)
        return None
