"""
Loan Readiness Score Service for the AI Loan Decision Platform.

Computes a user-friendly readiness score (0-100) that is distinct from
the Approval_Probability. Based on weighted financial factors with
normalization to a 0-100 scale.

Formula (from design document):
    LRS = (credit_score_normalized * 0.30) +
          (dti_ratio_score * 0.25) +
          (credit_utilization_score * 0.20) +
          (employment_length_score * 0.15) +
          (existing_loans_score * 0.10)

Categories:
    0-25:  Poor (red)
    26-50: Fair (orange)
    51-75: Good (yellow)
    76-100: Excellent (green)

Requirements: 9.1, 9.2, 9.3, 9.4, 9.5
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Weights for each factor (Requirement 9.2)
WEIGHT_CREDIT_SCORE = 0.30
WEIGHT_DTI_RATIO = 0.25
WEIGHT_CREDIT_UTILIZATION = 0.20
WEIGHT_EMPLOYMENT_LENGTH = 0.15
WEIGHT_EXISTING_LOANS = 0.10

# Factor names for improvement area reporting
FACTOR_NAMES = {
    "credit_score": "Credit Score",
    "dti_ratio": "Debt-to-Income Ratio",
    "credit_utilization": "Credit Utilization",
    "employment_length": "Employment Length",
    "existing_loans": "Number of Existing Loans",
}

FACTOR_WEIGHTS = {
    "credit_score": WEIGHT_CREDIT_SCORE,
    "dti_ratio": WEIGHT_DTI_RATIO,
    "credit_utilization": WEIGHT_CREDIT_UTILIZATION,
    "employment_length": WEIGHT_EMPLOYMENT_LENGTH,
    "existing_loans": WEIGHT_EXISTING_LOANS,
}


def _normalize_credit_score(credit_score: float) -> float:
    """Normalize credit score (300-850) to 0-100 scale.

    Formula: (credit_score - 300) / (850 - 300) * 100
    """
    return (credit_score - 300) / (850 - 300) * 100


def _normalize_dti_ratio(dti_ratio: float) -> float:
    """Normalize DTI ratio (0-100) to 0-100 score. Lower DTI = better.

    Formula: (1 - dti_ratio / 100) * 100
    """
    return (1 - dti_ratio / 100) * 100


def _normalize_credit_utilization(credit_utilization: float) -> float:
    """Normalize credit utilization (0-100) to 0-100 score. Lower = better.

    Formula: (1 - credit_utilization / 100) * 100
    """
    return (1 - credit_utilization / 100) * 100


def _normalize_employment_length(employment_length: float) -> float:
    """Normalize employment length (years) to 0-100 score. Capped at 10 years.

    Formula: min(employment_length / 10, 1) * 100
    """
    return min(employment_length / 10, 1) * 100


def _normalize_existing_loans(existing_loans: float) -> float:
    """Normalize existing loans count to 0-100 score. Fewer = better, capped at 10.

    Formula: max(0, (1 - existing_loans / 10)) * 100
    """
    return max(0, (1 - existing_loans / 10)) * 100


def map_readiness_category(score: float) -> str:
    """Map numeric readiness score (0-100) to category.

    Categories (Requirement 9.3):
        0-25:  Poor
        26-50: Fair
        51-75: Good
        76-100: Excellent
    """
    if score <= 25:
        return "Poor"
    elif score <= 50:
        return "Fair"
    elif score <= 75:
        return "Good"
    else:
        return "Excellent"


class LoanReadinessService:
    """Computes the Loan Readiness Score and improvement recommendations.

    The readiness score is a weighted combination of normalized financial
    factors, providing a user-friendly indicator of loan readiness that
    is distinct from the ML-based Approval_Probability.
    """

    def compute(self, application_data: dict) -> dict:
        """
        Compute the Loan Readiness Score for a loan application.

        Args:
            application_data: Dict matching LoanApplicationInput fields.
                Required keys: credit_score, dti_ratio, credit_utilization,
                employment_length, existing_loans.

        Returns:
            Dict with:
            - loan_readiness_score (float, 0-100)
            - readiness_category (str: Poor/Fair/Good/Excellent)
            - improvement_areas (list of dicts, top 3 if score < 50)

        Raises:
            ValueError: If required fields are missing or invalid.
        """
        try:
            # Extract required fields
            credit_score = float(application_data["credit_score"])
            dti_ratio = float(application_data["dti_ratio"])
            credit_utilization = float(application_data["credit_utilization"])
            employment_length = float(application_data["employment_length"])
            existing_loans = float(application_data["existing_loans"])
        except (KeyError, TypeError, ValueError) as e:
            logger.error("Failed to compute readiness score — invalid input: %s", e)
            raise ValueError(f"Missing or invalid input for readiness score: {e}")

        # Normalize each factor to 0-100 scale
        credit_score_normalized = _normalize_credit_score(credit_score)
        dti_ratio_score = _normalize_dti_ratio(dti_ratio)
        credit_utilization_score = _normalize_credit_utilization(credit_utilization)
        employment_length_score = _normalize_employment_length(employment_length)
        existing_loans_score = _normalize_existing_loans(existing_loans)

        # Compute weighted sum (Requirement 9.2)
        loan_readiness_score = (
            credit_score_normalized * WEIGHT_CREDIT_SCORE
            + dti_ratio_score * WEIGHT_DTI_RATIO
            + credit_utilization_score * WEIGHT_CREDIT_UTILIZATION
            + employment_length_score * WEIGHT_EMPLOYMENT_LENGTH
            + existing_loans_score * WEIGHT_EXISTING_LOANS
        )

        # Clamp to 0-100 range
        loan_readiness_score = max(0.0, min(100.0, loan_readiness_score))
        loan_readiness_score = round(loan_readiness_score, 2)

        # Determine category
        readiness_category = map_readiness_category(loan_readiness_score)

        # Compute improvement areas if score < 50 (Requirement 9.4)
        improvement_areas: list[dict] = []
        if loan_readiness_score < 50:
            improvement_areas = self._compute_improvement_areas(
                credit_score_normalized,
                dti_ratio_score,
                credit_utilization_score,
                employment_length_score,
                existing_loans_score,
            )

        return {
            "loan_readiness_score": loan_readiness_score,
            "readiness_category": readiness_category,
            "improvement_areas": improvement_areas,
        }

    def _compute_improvement_areas(
        self,
        credit_score_normalized: float,
        dti_ratio_score: float,
        credit_utilization_score: float,
        employment_length_score: float,
        existing_loans_score: float,
    ) -> list[dict]:
        """
        Identify top 3 improvement areas ranked by weighted factor deficit.

        The deficit is calculated as: weight * (100 - normalized_score)
        This represents how much each factor is dragging down the total score.

        Requirement 9.4: When score < 50, highlight top 3 improvement areas
        ranked by their weighted factor contribution deficit.

        Returns:
            List of top 3 improvement area dicts with:
            - factor: factor key name
            - display_name: human-readable factor name
            - current_score: normalized score (0-100)
            - weight: factor weight
            - deficit: weighted deficit value
            - recommendation: actionable improvement suggestion
        """
        factor_scores = {
            "credit_score": credit_score_normalized,
            "dti_ratio": dti_ratio_score,
            "credit_utilization": credit_utilization_score,
            "employment_length": employment_length_score,
            "existing_loans": existing_loans_score,
        }

        # Calculate weighted deficit for each factor
        deficits = []
        for factor, score in factor_scores.items():
            weight = FACTOR_WEIGHTS[factor]
            deficit = weight * (100 - score)
            deficits.append({
                "factor": factor,
                "display_name": FACTOR_NAMES[factor],
                "current_score": round(score, 2),
                "weight": weight,
                "deficit": round(deficit, 2),
                "recommendation": self._get_recommendation(factor, score),
            })

        # Sort by deficit descending (largest deficit = most room for improvement)
        deficits.sort(key=lambda x: x["deficit"], reverse=True)

        # Return top 3
        return deficits[:3]

    def _get_recommendation(self, factor: str, current_score: float) -> str:
        """Generate an actionable recommendation for a given factor.

        Args:
            factor: Factor key name.
            current_score: Current normalized score (0-100).

        Returns:
            Human-readable recommendation string.
        """
        if factor == "credit_score":
            if current_score < 30:
                return "Focus on building your credit history. Consider secured credit cards and timely bill payments."
            elif current_score < 60:
                return "Continue improving your credit score by maintaining on-time payments and reducing outstanding balances."
            else:
                return "Your credit score is reasonable. Keep maintaining good payment habits."

        elif factor == "dti_ratio":
            if current_score < 30:
                return "Your debt-to-income ratio is high. Consider paying down existing debts or increasing your income."
            elif current_score < 60:
                return "Try to reduce your monthly debt obligations to improve your debt-to-income ratio."
            else:
                return "Your debt-to-income ratio is manageable. Avoid taking on new debt."

        elif factor == "credit_utilization":
            if current_score < 30:
                return "Your credit utilization is very high. Try to keep balances below 30% of your credit limits."
            elif current_score < 60:
                return "Reduce your credit card balances to lower your utilization rate."
            else:
                return "Your credit utilization is reasonable. Continue keeping balances low."

        elif factor == "employment_length":
            if current_score < 30:
                return "Longer employment history strengthens your application. Stay in your current position if possible."
            elif current_score < 60:
                return "Continue building your employment tenure. Stability is valued by lenders."
            else:
                return "Your employment length is adequate. Maintain job stability."

        elif factor == "existing_loans":
            if current_score < 30:
                return "You have many active loans. Consider consolidating or paying off some before applying."
            elif current_score < 60:
                return "Try to reduce the number of active loans to improve your profile."
            else:
                return "Your number of existing loans is manageable."

        return "Improve this factor to increase your readiness score."


# Singleton instance
_readiness_service: Optional[LoanReadinessService] = None


def get_readiness_service() -> LoanReadinessService:
    """Get or create the LoanReadinessService singleton."""
    global _readiness_service
    if _readiness_service is None:
        _readiness_service = LoanReadinessService()
    return _readiness_service
