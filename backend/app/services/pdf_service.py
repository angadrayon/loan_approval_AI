"""
PDF Report Generation Service for the AI Loan Decision Platform.

Generates downloadable PDF assessment reports using fpdf2.
Uses human-friendly formatting matching the assessment page UI.

Requirements: 13.1, 13.2, 13.3, 13.4, 13.5
"""

import logging
from fpdf import FPDF

logger = logging.getLogger(__name__)

# Feature display names and advice generators (mirrors frontend CounterfactualCards)
FEATURE_CONFIG = {
    "credit_score": {
        "label": "Credit Score",
        "why": "A stronger credit score signals lower lending risk and improves lender confidence.",
        "advice": lambda c, t: f"Improve your credit score from {round(c)} to around {round(t)}+",
        "action_plan": lambda c, t: [
            "Pay all EMIs and credit card bills on time",
            "Reduce credit utilization below 30%",
            "Avoid applying for multiple loans simultaneously",
            "Clear outstanding overdue payments",
        ],
    },
    "monthly_income": {
        "label": "Monthly Income",
        "why": "Higher income demonstrates stronger repayment capacity and lowers lending risk.",
        "advice": lambda c, t: f"Increase your monthly income from Rs.{round(c):,} to at least Rs.{round(t):,}",
        "action_plan": lambda c, t: [
            "Increase working hours or overtime income",
            "Add a secondary income source",
            "Seek salary growth before reapplying",
            "Demonstrate stable income for several months",
        ],
    },
    "dti_ratio": {
        "label": "Debt-to-Income Ratio",
        "why": "Lower debt obligations improve your ability to repay new loans.",
        "advice": lambda c, t: f"Reduce your debt-to-income ratio from {round(c)}% to below {round(t)}%",
        "action_plan": lambda c, t: [
            "Pay off existing loans where possible",
            "Reduce monthly EMI obligations",
            "Avoid taking additional debt before applying",
            "Increase income to improve debt coverage",
        ],
    },
    "employment_length": {
        "label": "Employment History",
        "why": "Stable employment indicates consistent income and lower risk.",
        "advice": lambda c, t: "Build a longer employment history before applying" if c < 2 else f"Maintain employment stability for at least {round(t)} years",
        "action_plan": lambda c, t: [
            "Maintain stable employment for at least 12-24 months",
            "Avoid frequent job switching before applying",
            "Provide consistent income records",
            "Keep salary slips and employment letters ready",
        ],
    },
    "credit_utilization": {
        "label": "Credit Utilization",
        "why": "Lower utilization shows responsible credit management.",
        "advice": lambda c, t: f"Reduce your credit utilization from {round(c)}% to below {round(t)}%",
        "action_plan": lambda c, t: [
            "Pay down credit card balances before applying",
            "Request credit limit increases without spending more",
            "Spread balances across multiple cards",
            "Avoid maxing out any single credit card",
        ],
    },
    "existing_loans": {
        "label": "Existing Loans",
        "why": "Fewer active loans improve your debt profile.",
        "advice": lambda c, t: f"Pay off at least {round(c - t)} existing loans before applying" if (c - t) > 1 else "Reduce outstanding loans before applying for additional credit",
        "action_plan": lambda c, t: [
            "Prioritize closing loans with highest EMI",
            "Avoid taking new loans before applying",
            "Consider loan consolidation",
            "Maintain clean repayment records on remaining loans",
        ],
    },
    "monthly_emi": {
        "label": "Monthly EMI",
        "why": "Smaller monthly obligations improve affordability.",
        "advice": lambda c, t: f"Lower your monthly EMI from Rs.{round(c):,} to around Rs.{round(t):,}",
        "action_plan": lambda c, t: [
            "Prepay or close high-EMI loans",
            "Refinance existing loans for lower EMIs",
            "Avoid new EMI commitments before applying",
            "Consider extending loan tenure to reduce monthly burden",
        ],
    },
    "loan_amount_requested": {
        "label": "Loan Amount",
        "why": "Smaller loans are generally easier to approve and carry lower risk.",
        "advice": lambda c, t: f"Consider requesting Rs.{round(t):,} instead of Rs.{round(c):,}",
        "action_plan": lambda c, t: [
            "Apply for a smaller amount and increase later",
            "Improve other factors first, then apply for the full amount",
            "Save a larger down payment to reduce loan requirement",
            "Consider splitting into multiple smaller loans",
        ],
    },
    "employment_status_encoded": {
        "label": "Employment Status",
        "why": "Stable employment type improves lender confidence.",
        "advice": lambda c, t: "Secure stable employment before applying",
        "action_plan": lambda c, t: [
            "Secure full-time employment before applying",
            "Provide employment verification documents",
            "Show consistent income for at least 6 months",
            "Demonstrate job stability",
        ],
    },
}

SHAP_EXPLANATIONS = {
    "credit_score": {
        "positive": "Your credit score is strong and positively contributed to your assessment.",
        "negative": "Your credit score is below preferred lending thresholds and negatively impacted approval chances.",
    },
    "monthly_income": {
        "positive": "Your income level demonstrates strong repayment capacity.",
        "negative": "Your income may be insufficient for the requested loan amount.",
    },
    "dti_ratio": {
        "positive": "Your debt-to-income ratio is healthy, showing manageable debt levels.",
        "negative": "Your debt-to-income ratio is high, indicating heavy existing obligations.",
    },
    "employment_length": {
        "positive": "Your employment history shows stability and consistent income.",
        "negative": "Your employment history is relatively short, which increases perceived risk.",
    },
    "credit_utilization": {
        "positive": "Your credit utilization is low, showing responsible credit management.",
        "negative": "Your credit utilization is high, suggesting heavy reliance on credit.",
    },
    "existing_loans": {
        "positive": "Your number of active loans is manageable.",
        "negative": "You have many active loans, which increases your debt burden.",
    },
    "monthly_emi": {
        "positive": "Your monthly loan payments are reasonable relative to income.",
        "negative": "Your monthly loan payments are high relative to income.",
    },
    "loan_amount_requested": {
        "positive": "The requested loan amount is reasonable for your profile.",
        "negative": "The requested loan amount may be too high for your current profile.",
    },
    "employment_status_encoded": {
        "positive": "Your employment type is favorable for lending decisions.",
        "negative": "Your employment type may increase perceived lending risk.",
    },
    "age": {
        "positive": "Your age is favorable for this assessment.",
        "negative": "Your age is a minor factor in this assessment.",
    },
}


class PDFReportService:
    """Generates PDF assessment reports with human-friendly formatting."""

    def generate(
        self,
        application: dict,
        prediction: dict,
        shap_values: list[dict],
        counterfactuals: list[dict],
        applicant_name: str = "Applicant",
    ) -> bytes:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)

        # Title
        pdf.set_font("Helvetica", "B", 18)
        pdf.cell(0, 12, "AI Loan Decision Platform", ln=True, align="C")
        pdf.set_font("Helvetica", "", 12)
        pdf.cell(0, 8, "Credit Risk Assessment Report", ln=True, align="C")
        pdf.ln(10)

        # Applicant Information
        self._section_header(pdf, "Applicant Information")
        pdf.set_font("Helvetica", "", 10)
        fields = [
            ("Name", applicant_name),
            ("Age", str(round(application.get("age", 0)))),
            ("Monthly Income", f"Rs.{round(application.get('monthly_income', 0)):,}"),
            ("Employment Status", str(application.get("employment_status", "-"))),
            ("Employment Length", f"{round(application.get('employment_length', 0))} years"),
            ("Credit Score", str(round(application.get("credit_score", 0)))),
            ("Existing Loans", str(round(application.get("existing_loans", 0)))),
            ("Monthly EMI", f"Rs.{round(application.get('monthly_emi', 0)):,}"),
            ("DTI Ratio", f"{round(application.get('dti_ratio', 0))}%"),
            ("Credit Utilization", f"{round(application.get('credit_utilization', 0))}%"),
            ("Loan Amount Requested", f"Rs.{round(application.get('loan_amount_requested', 0)):,}"),
        ]
        for label, value in fields:
            pdf.cell(60, 6, f"{label}:", ln=False)
            pdf.cell(0, 6, value, ln=True)
        pdf.ln(8)

        # Risk Assessment
        self._section_header(pdf, "Risk Assessment")
        pdf.set_font("Helvetica", "", 10)
        decision = prediction.get("decision", "-")
        pdf.cell(60, 7, "Decision:", ln=False)
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 7, decision, ln=True)
        pdf.set_font("Helvetica", "", 10)

        metrics = [
            ("Approval Probability", f"{round(prediction.get('approval_probability', 0))}%"),
            ("Risk Score", str(round(prediction.get("risk_score", 0)))),
            ("Risk Level", str(prediction.get("risk_level", "-"))),
            ("Loan Readiness Score", str(round(prediction.get("loan_readiness_score", 0)))),
            ("Readiness Category", str(prediction.get("readiness_category", "-"))),
        ]
        for label, value in metrics:
            pdf.cell(60, 6, f"{label}:", ln=False)
            pdf.cell(0, 6, value, ln=True)
        pdf.ln(8)

        # Explanation
        self._section_header(pdf, "Key Factors")
        pdf.set_font("Helvetica", "", 10)
        if shap_values:
            sorted_shap = sorted(shap_values, key=lambda x: abs(x.get("shap_value", 0)), reverse=True)[:5]
            for sv in sorted_shap:
                feature = sv.get("feature_name", sv.get("feature", "unknown"))
                direction = sv.get("direction", "negative")
                explanation = self._get_shap_explanation(feature, direction)
                label = FEATURE_CONFIG.get(feature, {}).get("label", feature.replace("_", " ").title())
                pdf.set_font("Helvetica", "B", 10)
                pdf.cell(0, 6, f"  {label}", ln=True)
                pdf.set_font("Helvetica", "", 9)
                pdf.multi_cell(0, 5, f"    {explanation}")
                pdf.ln(2)
        else:
            pdf.cell(0, 6, "  Detailed explanations not available.", ln=True)
        pdf.ln(5)

        # Recommendations
        self._section_header(pdf, "Recommendations")
        pdf.set_font("Helvetica", "", 10)

        if decision == "Rejected" and counterfactuals:
            approval_prob = prediction.get("approval_probability", 0)
            for idx, cf in enumerate(counterfactuals):
                feature = cf.get("feature_name", cf.get("feature", "unknown"))
                current = cf.get("current_value", 0)
                target = cf.get("recommended_value", 0)
                impact = cf.get("estimated_impact", cf.get("projected_approval_probability", 50))

                config = FEATURE_CONFIG.get(feature, None)
                if config:
                    advice = config["advice"](current, target)
                    why = config["why"]
                    label = config["label"]
                    actions = config["action_plan"](current, target)
                else:
                    advice = f"Improve {feature.replace('_', ' ')}"
                    why = "This factor impacts your approval chances."
                    label = feature.replace("_", " ").title()
                    actions = ["Work on improving this factor before reapplying"]

                pdf.set_font("Helvetica", "B", 10)
                pdf.cell(0, 6, f"  Priority {idx + 1}: {label}", ln=True)
                pdf.set_font("Helvetica", "", 9)
                pdf.multi_cell(0, 5, f"    Recommendation: {advice}")
                pdf.ln(1)
                pdf.set_font("Helvetica", "I", 9)
                pdf.cell(0, 5, "    Action Plan:", ln=True)
                pdf.set_font("Helvetica", "", 9)
                for action in actions[:4]:
                    pdf.cell(0, 5, f"      - {action}", ln=True)
                pdf.ln(1)
                pdf.set_font("Helvetica", "", 9)
                pdf.multi_cell(0, 5, f"    Why it matters: {why}")
                pdf.multi_cell(0, 5, f"    Potential outcome: Approval probability could increase from {round(approval_prob)}% to {round(impact)}%.")
                pdf.ln(4)

        elif decision == "Approved" and shap_values:
            positive = [sv for sv in shap_values if sv.get("direction") == "positive"]
            top_positive = sorted(positive, key=lambda x: abs(x.get("shap_value", 0)), reverse=True)[:3]
            pdf.cell(0, 6, "  Key strengths that contributed to your approval:", ln=True)
            pdf.ln(2)
            for sv in top_positive:
                feature = sv.get("feature_name", sv.get("feature", "unknown"))
                label = FEATURE_CONFIG.get(feature, {}).get("label", feature.replace("_", " ").title())
                explanation = self._get_shap_explanation(feature, "positive")
                pdf.set_font("Helvetica", "B", 9)
                pdf.cell(0, 5, f"    {label}", ln=True)
                pdf.set_font("Helvetica", "", 9)
                pdf.multi_cell(0, 5, f"      {explanation}")
                pdf.ln(1)
        else:
            pdf.cell(0, 6, "  No specific recommendations available.", ln=True)

        # Footer
        pdf.ln(15)
        pdf.set_font("Helvetica", "I", 8)
        pdf.cell(0, 5, "This report is generated by the AI Loan Decision Platform for informational purposes.", ln=True, align="C")
        pdf.cell(0, 5, "It does not constitute financial advice. Please consult a financial advisor.", ln=True, align="C")

        return pdf.output()

    def _section_header(self, pdf: FPDF, title: str):
        pdf.set_font("Helvetica", "B", 14)
        pdf.cell(0, 10, title, ln=True)
        pdf.set_draw_color(200, 200, 200)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(3)

    def _get_shap_explanation(self, feature: str, direction: str) -> str:
        config = SHAP_EXPLANATIONS.get(feature, None)
        if config:
            return config.get(direction, "This factor influenced your assessment.")
        return "This factor helped your application." if direction == "positive" else "This factor worked against your application."


_pdf_service = None


def get_pdf_service() -> PDFReportService:
    global _pdf_service
    if _pdf_service is None:
        _pdf_service = PDFReportService()
    return _pdf_service
