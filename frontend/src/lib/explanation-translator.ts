/**
 * Explanation Translator — converts technical ML outputs to plain language.
 *
 * Maps technical feature names to user-friendly equivalents and generates
 * plain-language explanations for SHAP values and counterfactuals.
 *
 * Requirements: 20.1, 20.2, 20.3, 20.4, 20.5, 20.6
 */

// Technical → Plain language feature name mapping
const FEATURE_DISPLAY_MAP: Record<string, string> = {
  age: "Your age",
  monthly_income: "Your monthly income",
  employment_status_encoded: "Your employment status",
  employment_status: "Your employment status",
  employment_length: "How long you've been at your current job",
  credit_score: "Your credit score",
  existing_loans: "Number of current active loans",
  monthly_emi: "Your current monthly loan payments",
  dti_ratio: "Portion of income going toward debt",
  credit_utilization: "How much of your credit limit you're using",
  loan_amount_requested: "The loan amount you requested",
};

/**
 * Get the plain-language display name for a technical feature.
 */
export function getFeatureDisplayName(technicalName: string): string {
  return FEATURE_DISPLAY_MAP[technicalName] || technicalName.replace(/_/g, " ");
}

/**
 * Translate a SHAP value into a plain-language explanation.
 */
export function translateShapValue(
  featureName: string,
  featureValue: number,
  direction: string
): string {
  const displayName = getFeatureDisplayName(featureName);
  const helped = direction === "positive";

  switch (featureName) {
    case "credit_score":
      return helped
        ? `${displayName} (${featureValue.toFixed(0)}) is strong and helped your application.`
        : `${displayName} (${featureValue.toFixed(0)}) is below average and worked against your application.`;
    case "dti_ratio":
      return helped
        ? `${displayName} (${featureValue.toFixed(0)}%) is low, which is favorable.`
        : `${displayName} (${featureValue.toFixed(0)}%) is high, meaning too much income goes to debt.`;
    case "credit_utilization":
      return helped
        ? `${displayName} (${featureValue.toFixed(0)}%) is low, showing responsible credit use.`
        : `${displayName} (${featureValue.toFixed(0)}%) is high, suggesting heavy reliance on credit.`;
    case "monthly_income":
      return helped
        ? `${displayName} ($${featureValue.toLocaleString()}) demonstrates strong earning capacity.`
        : `${displayName} ($${featureValue.toLocaleString()}) may be insufficient for the requested amount.`;
    case "employment_length":
      return helped
        ? `${displayName} (${featureValue.toFixed(0)} years) shows stability.`
        : `${displayName} (${featureValue.toFixed(0)} years) is relatively short.`;
    case "existing_loans":
      return helped
        ? `${displayName} (${featureValue.toFixed(0)}) is manageable.`
        : `${displayName} (${featureValue.toFixed(0)}) is high, indicating heavy existing obligations.`;
    case "monthly_emi":
      return helped
        ? `${displayName} ($${featureValue.toLocaleString()}) is reasonable relative to income.`
        : `${displayName} ($${featureValue.toLocaleString()}) is high relative to income.`;
    case "loan_amount_requested":
      return helped
        ? `The requested amount ($${featureValue.toLocaleString()}) is reasonable for your profile.`
        : `The requested amount ($${featureValue.toLocaleString()}) may be too high for your current profile.`;
    case "age":
      return helped
        ? `${displayName} (${featureValue.toFixed(0)}) is favorable for this assessment.`
        : `${displayName} (${featureValue.toFixed(0)}) is a minor factor in this assessment.`;
    default:
      return helped
        ? `This factor helped your application.`
        : `This factor worked against your application.`;
  }
}

/**
 * Translate a counterfactual recommendation into plain language.
 */
export function translateCounterfactual(
  featureName: string,
  currentValue: number,
  recommendedValue: number,
  projectedApproval: number
): string {
  const displayName = getFeatureDisplayName(featureName);

  switch (featureName) {
    case "credit_score":
      return `If you improve your credit score from ${currentValue.toFixed(0)} to ${recommendedValue.toFixed(0)}, your approval chances could improve to ${projectedApproval.toFixed(0)}%.`;
    case "dti_ratio":
      return `If you reduce your debt-to-income ratio from ${currentValue.toFixed(0)}% to ${recommendedValue.toFixed(0)}%, your approval chances could improve to ${projectedApproval.toFixed(0)}%.`;
    case "credit_utilization":
      return `If you reduce your credit utilization from ${currentValue.toFixed(0)}% to ${recommendedValue.toFixed(0)}%, your approval chances could improve to ${projectedApproval.toFixed(0)}%.`;
    case "monthly_income":
      return `If you increase your monthly income from $${currentValue.toLocaleString()} to $${recommendedValue.toLocaleString()}, your approval chances could improve to ${projectedApproval.toFixed(0)}%.`;
    case "monthly_emi":
      return `If you reduce your monthly payments from $${currentValue.toLocaleString()} to $${recommendedValue.toLocaleString()}, your approval chances could improve to ${projectedApproval.toFixed(0)}%.`;
    case "existing_loans":
      return `If you reduce your active loans from ${currentValue.toFixed(0)} to ${recommendedValue.toFixed(0)}, your approval chances could improve to ${projectedApproval.toFixed(0)}%.`;
    case "loan_amount_requested":
      return `If you request $${recommendedValue.toLocaleString()} instead of $${currentValue.toLocaleString()}, your approval chances could improve to ${projectedApproval.toFixed(0)}%.`;
    default:
      return `If you change ${displayName} from ${currentValue.toFixed(1)} to ${recommendedValue.toFixed(1)}, your approval chances could improve to ${projectedApproval.toFixed(0)}%.`;
  }
}

/**
 * Translate a readiness score into an interpretation.
 */
export function translateReadinessScore(score: number, category: string): string {
  switch (category) {
    case "Excellent":
      return "Your financial profile is excellent. You are well-positioned for loan approval.";
    case "Good":
      return "Your financial profile is good. Minor improvements could further strengthen your application.";
    case "Fair":
      return "Your financial profile has room for improvement. Focus on the areas highlighted below.";
    case "Poor":
      return "Your financial profile needs significant improvement before applying for a loan.";
    default:
      return `Your readiness score is ${score.toFixed(0)} out of 100.`;
  }
}
