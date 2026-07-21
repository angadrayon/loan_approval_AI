"""
Audit Service for the AI Loan Decision Platform.

Handles audit log persistence for all system events including:
- Prediction events (inputs, outputs, SHAP values, counterfactuals)
- Authentication events (login, logout, failed attempts)
- Administrative actions (role changes, reviews)

Implements retry logic with exponential backoff and deferred writing
on persistent failures.

Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6
"""

import logging
import time
from collections import deque
from datetime import datetime, timezone
from typing import Any, Optional

from app.models.repository import create_audit_log, get_audit_logs

logger = logging.getLogger(__name__)

# Retry configuration (Requirement 12.6)
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = [1, 2, 4]  # Exponential backoff: 1s, 2s, 4s

# Deferred write queue for failed audit logs
_deferred_queue: deque = deque(maxlen=1000)

# Flag to indicate audit logging failure (for admin dashboard warning)
_audit_failure_detected: bool = False


class AuditService:
    """Handles audit log persistence with retry and deferred writing.

    All audit records are immutable (write-only, no update/delete)
    per Requirement 12.2.
    """

    def log_prediction(
        self,
        user_id: str,
        application_id: str,
        inputs: dict,
        outputs: dict,
        shap_values: Optional[list[dict]] = None,
        counterfactuals: Optional[list[dict]] = None,
        ip_address: Optional[str] = None,
    ) -> bool:
        """
        Log a prediction event with full audit trail.

        Records: applicant inputs, prediction outputs, SHAP values,
        counterfactual recommendations, timestamp, and user ID.

        Requirement 12.1.

        Args:
            user_id: The authenticated user's ID.
            application_id: The loan application UUID.
            inputs: Dict of all application input fields.
            outputs: Dict with approval_probability, risk_score,
                     default_probability, decision.
            shap_values: List of SHAP value dicts (optional).
            counterfactuals: List of counterfactual dicts (optional).
            ip_address: Client IP address (optional).

        Returns:
            True if the log was persisted, False if deferred.
        """
        event_data: dict[str, Any] = {
            "application_id": application_id,
            "inputs": inputs,
            "outputs": outputs,
            "decision": outputs.get("decision"),
        }

        if shap_values is not None:
            event_data["shap_values"] = shap_values

        if counterfactuals is not None:
            event_data["counterfactuals"] = counterfactuals

        return self._write_log(
            user_id=user_id,
            event_type="prediction",
            event_data=event_data,
            ip_address=ip_address,
        )

    def log_auth_event(
        self,
        event_type: str,
        user_id: Optional[str] = None,
        email: Optional[str] = None,
        ip_address: Optional[str] = None,
        success: bool = True,
    ) -> bool:
        """
        Log an authentication event.

        Records login, logout, and failed login attempts with
        timestamp and IP address.

        Requirement 12.5.

        Args:
            event_type: One of "login", "logout", "login_failed".
            user_id: User ID (may be None for failed attempts).
            email: Email used in the attempt (for failed logins).
            ip_address: Client IP address.
            success: Whether the auth action succeeded.

        Returns:
            True if the log was persisted, False if deferred.
        """
        event_data: dict[str, Any] = {
            "success": success,
        }

        if email:
            event_data["email"] = email

        return self._write_log(
            user_id=user_id,
            event_type=f"auth.{event_type}",
            event_data=event_data,
            ip_address=ip_address,
        )

    def log_admin_action(
        self,
        user_id: str,
        action: str,
        target_user_id: Optional[str] = None,
        details: Optional[dict] = None,
        ip_address: Optional[str] = None,
    ) -> bool:
        """
        Log an administrative action (e.g., role change, review).

        Args:
            user_id: The admin/officer performing the action.
            action: Action type (e.g., "role_change", "application_review").
            target_user_id: The user being acted upon (if applicable).
            details: Additional action details.
            ip_address: Client IP address.

        Returns:
            True if the log was persisted, False if deferred.
        """
        event_data: dict[str, Any] = {
            "action": action,
        }

        if target_user_id:
            event_data["target_user_id"] = target_user_id

        if details:
            event_data.update(details)

        return self._write_log(
            user_id=user_id,
            event_type=f"admin.{action}",
            event_data=event_data,
            ip_address=ip_address,
        )

    def get_logs(
        self,
        page: int = 1,
        page_size: int = 50,
        filters: Optional[dict] = None,
    ) -> tuple[list[dict], int]:
        """
        Retrieve audit logs with pagination and filtering.

        Sorted by timestamp descending (most recent first).
        Supports filtering by date_from, date_to, user_id, decision.

        Requirement 12.3.

        Args:
            page: Page number (1-indexed).
            page_size: Items per page (default 50).
            filters: Optional dict with date_from, date_to, user_id, decision.

        Returns:
            Tuple of (list of audit log dicts, total count).
        """
        return get_audit_logs(page=page, page_size=page_size, filters=filters)

    def get_logs_for_application(
        self, application_id: str
    ) -> list[dict]:
        """
        Retrieve all audit logs for a specific application.

        Returns logs in chronological order (oldest first) for
        displaying the audit trail of a specific application.

        Requirement 12.4.

        Args:
            application_id: The loan application UUID.

        Returns:
            List of audit log dicts for the application.
        """
        # Get all logs and filter by application_id in event_data
        # Note: This uses the repository's JSONB filtering capability
        logs, _ = get_audit_logs(
            page=1,
            page_size=1000,  # Get all for this application
            filters=None,
        )

        # Filter by application_id in event_data
        application_logs = [
            log for log in logs
            if log.get("event_data", {}).get("application_id") == application_id
        ]

        # Return in chronological order (oldest first)
        application_logs.sort(key=lambda x: x.get("created_at", ""))

        return application_logs

    def _write_log(
        self,
        user_id: Optional[str],
        event_type: str,
        event_data: dict,
        ip_address: Optional[str] = None,
    ) -> bool:
        """
        Write an audit log with retry logic.

        Implements exponential backoff (1s, 2s, 4s) with up to 3 retries.
        On persistent failure, queues the record for deferred writing.

        Requirement 12.6.

        Args:
            user_id: User ID (may be None for system events).
            event_type: Type of event being logged.
            event_data: Event payload data.
            ip_address: Client IP address.

        Returns:
            True if persisted successfully, False if deferred.
        """
        global _audit_failure_detected

        log_data = {
            "user_id": user_id,
            "event_type": event_type,
            "event_data": event_data,
            "ip_address": ip_address,
        }

        for attempt in range(MAX_RETRIES):
            try:
                create_audit_log(log_data)
                # If we had previous failures, try to flush deferred queue
                if _deferred_queue:
                    self._flush_deferred_queue()
                return True
            except Exception as e:
                if attempt < MAX_RETRIES - 1:
                    backoff = RETRY_BACKOFF_SECONDS[attempt]
                    logger.warning(
                        "Audit log write failed (attempt %d/%d), retrying in %ds: %s",
                        attempt + 1,
                        MAX_RETRIES,
                        backoff,
                        e,
                    )
                    time.sleep(backoff)
                else:
                    # All retries exhausted — queue for deferred writing
                    logger.error(
                        "Audit log write failed after %d retries — queuing for deferred write: %s",
                        MAX_RETRIES,
                        e,
                    )
                    _deferred_queue.append(log_data)
                    _audit_failure_detected = True
                    return False

        return False

    def _flush_deferred_queue(self):
        """Attempt to flush deferred audit logs to the database."""
        global _audit_failure_detected

        flushed = 0
        while _deferred_queue:
            log_data = _deferred_queue[0]
            try:
                create_audit_log(log_data)
                _deferred_queue.popleft()
                flushed += 1
            except Exception:
                # Still failing — stop trying
                break

        if flushed > 0:
            logger.info("Flushed %d deferred audit logs", flushed)

        if not _deferred_queue:
            _audit_failure_detected = False

    @staticmethod
    def has_audit_failure() -> bool:
        """Check if there are pending deferred audit logs.

        Used by the admin dashboard to display a warning indicator.

        Requirement 12.6.
        """
        return _audit_failure_detected

    @staticmethod
    def get_deferred_count() -> int:
        """Get the number of audit logs waiting in the deferred queue."""
        return len(_deferred_queue)


# Singleton instance
_audit_service: Optional[AuditService] = None


def get_audit_service() -> AuditService:
    """Get or create the AuditService singleton."""
    global _audit_service
    if _audit_service is None:
        _audit_service = AuditService()
    return _audit_service
