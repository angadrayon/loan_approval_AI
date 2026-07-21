"use client";

/**
 * CounterfactualCards — Actionable loan-officer-style improvement recommendations.
 *
 * Each recommendation includes:
 * - Clear advice
 * - Specific action plan steps
 * - Why it matters
 * - Potential outcome with approval probability
 * - Priority ranking
 */

interface Counterfactual {
  feature_name?: string;
  feature?: string;
  current_value: number;
  recommended_value: number;
  estimated_impact?: number;
  projected_approval_probability?: number;
}

interface CounterfactualCardsProps {
  counterfactuals: Counterfactual[];
  currentApprovalProbability?: number;
}

interface RecommendationCard {
  icon: string;
  title: string;
  recommendation: string;
  actionPlan: string[];
  whyItMatters: string;
  potentialOutcome: string;
  impact: number;
  priority: number;
}

const FEATURE_CONFIG: Record<string, {
  label: string;
  icon: string;
  whyItMatters: string;
  actionPlan: (current: number, target: number) => string[];
  generateAdvice: (current: number, target: number) => string;
}> = {
  credit_score: {
    label: "Credit Score",
    icon: "📊",
    whyItMatters: "A stronger credit score signals lower lending risk and improves lender confidence.",
    actionPlan: (current, target) => [
      "Pay all EMIs and credit card bills on time",
      "Reduce credit utilization below 30%",
      "Avoid applying for multiple loans simultaneously",
      "Clear outstanding overdue payments",
      current < 500 ? "Consider a secured credit card to rebuild credit" : "Maintain consistent payment history for 6+ months",
    ],
    generateAdvice: (current, target) => `Improve your credit score from ${Math.round(current)} to around ${Math.round(target)}+`,
  },
  monthly_income: {
    label: "Monthly Income",
    icon: "💰",
    whyItMatters: "Higher income demonstrates stronger repayment capacity and lowers lending risk.",
    actionPlan: (current, target) => [
      "Increase working hours or overtime income",
      "Add a secondary income source",
      "Seek salary growth before reapplying",
      "Demonstrate stable income for several months",
      target > current * 2 ? "Consider applying after a significant income increase" : "Document all income sources for your application",
    ],
    generateAdvice: (current, target) => `Increase your monthly income from ₹${Math.round(current).toLocaleString("en-IN")} to at least ₹${Math.round(target).toLocaleString("en-IN")}`,
  },
  dti_ratio: {
    label: "Debt-to-Income Ratio",
    icon: "⚖️",
    whyItMatters: "Lower debt obligations improve your ability to repay new loans.",
    actionPlan: (current, target) => [
      "Pay off existing loans where possible",
      "Reduce monthly EMI obligations",
      "Avoid taking additional debt before applying",
      "Increase income to improve debt coverage",
      current > 60 ? "Prioritize clearing high-interest debt first" : "Consolidate loans for lower monthly payments",
    ],
    generateAdvice: (current, target) => `Reduce your debt-to-income ratio from ${Math.round(current)}% to below ${Math.round(target)}%`,
  },
  employment_length: {
    label: "Employment History",
    icon: "🏢",
    whyItMatters: "Stable employment indicates consistent income and lower risk.",
    actionPlan: (current, target) => [
      "Maintain stable employment for at least 12–24 months",
      "Avoid frequent job switching before applying",
      "Provide consistent income records",
      current < 1 ? "Wait until you have at least 1 year at your current job" : "Document your employment history clearly",
      "Keep salary slips and employment letters ready",
    ],
    generateAdvice: (current, target) => {
      if (current < 2) return "Build a longer employment history before applying";
      return `Maintain employment stability for at least ${Math.round(target)} years`;
    },
  },
  credit_utilization: {
    label: "Credit Utilization",
    icon: "💳",
    whyItMatters: "Lower utilization shows responsible credit management.",
    actionPlan: (current, target) => [
      "Pay down credit card balances before applying",
      "Request credit limit increases (without spending more)",
      "Spread balances across multiple cards",
      current > 70 ? "Aim to bring utilization below 30% as a priority" : "Keep utilization below 30% consistently",
      "Avoid maxing out any single credit card",
    ],
    generateAdvice: (current, target) => `Reduce your credit utilization from ${Math.round(current)}% to below ${Math.round(target)}%`,
  },
  existing_loans: {
    label: "Existing Loans",
    icon: "📋",
    whyItMatters: "Fewer active loans improve your debt profile and signal lower risk.",
    actionPlan: (current, target) => {
      const diff = Math.round(current - target);
      return [
        diff > 2 ? `Close at least ${diff} existing loans before applying` : "Pay off your smallest loan to reduce active count",
        "Prioritize closing loans with highest EMI",
        "Avoid taking new loans before applying",
        "Consider loan consolidation",
        "Maintain clean repayment records on remaining loans",
      ];
    },
    generateAdvice: (current, target) => {
      const diff = Math.round(current - target);
      if (diff <= 1) return "Reduce outstanding loans before applying for additional credit";
      return `Pay off at least ${diff} existing loans before applying`;
    },
  },
  monthly_emi: {
    label: "Monthly EMI",
    icon: "📅",
    whyItMatters: "Smaller monthly obligations improve affordability and repayment confidence.",
    actionPlan: (current, target) => [
      "Prepay or close high-EMI loans",
      "Refinance existing loans for lower EMIs",
      "Avoid new EMI commitments before applying",
      `Target reducing monthly EMI from ₹${Math.round(current).toLocaleString("en-IN")} to ₹${Math.round(target).toLocaleString("en-IN")}`,
      "Consider extending loan tenure to reduce monthly burden",
    ],
    generateAdvice: (current, target) => `Lower your monthly EMI from ₹${Math.round(current).toLocaleString("en-IN")} to around ₹${Math.round(target).toLocaleString("en-IN")}`,
  },
  loan_amount_requested: {
    label: "Loan Amount",
    icon: "🏦",
    whyItMatters: "Smaller loans are generally easier to approve and carry lower risk.",
    actionPlan: (current, target) => [
      `Consider requesting ₹${Math.round(target).toLocaleString("en-IN")} instead of ₹${Math.round(current).toLocaleString("en-IN")}`,
      "Apply for a smaller amount and increase later",
      "Improve other factors first, then apply for the full amount",
      "Consider splitting into multiple smaller loans",
      "Save a larger down payment to reduce loan requirement",
    ],
    generateAdvice: (current, target) => `Consider requesting ₹${Math.round(target).toLocaleString("en-IN")} instead of ₹${Math.round(current).toLocaleString("en-IN")}`,
  },
  employment_status_encoded: {
    label: "Employment Status",
    icon: "👔",
    whyItMatters: "Stable employment type improves lender confidence in repayment ability.",
    actionPlan: () => [
      "Secure full-time employment before applying",
      "Provide employment verification documents",
      "Show consistent income for at least 6 months",
      "Include offer letter or appointment letter",
      "Demonstrate job stability",
    ],
    generateAdvice: () => "Secure stable employment before applying",
  },
};

function buildRecommendation(cf: Counterfactual, currentApproval: number, priority: number): RecommendationCard {
  const featureName = cf.feature_name || cf.feature || "unknown";
  const config = FEATURE_CONFIG[featureName];
  const approvalProb = cf.projected_approval_probability || cf.estimated_impact || 50;

  if (!config) {
    return {
      icon: "💡",
      title: featureName.replace(/_/g, " "),
      recommendation: `Improve ${featureName.replace(/_/g, " ")}`,
      actionPlan: ["Work on improving this factor before reapplying"],
      whyItMatters: "This factor significantly impacts your approval chances.",
      potentialOutcome: `Approval probability could increase from ${Math.round(currentApproval)}% to ${Math.round(approvalProb)}%`,
      impact: approvalProb - currentApproval,
      priority,
    };
  }

  return {
    icon: config.icon,
    title: config.label,
    recommendation: config.generateAdvice(cf.current_value, cf.recommended_value),
    actionPlan: config.actionPlan(cf.current_value, cf.recommended_value),
    whyItMatters: config.whyItMatters,
    potentialOutcome: `Approval probability could increase from ${Math.round(currentApproval)}% to ${Math.round(approvalProb)}%`,
    impact: approvalProb - currentApproval,
    priority,
  };
}

export function CounterfactualCards({ counterfactuals, currentApprovalProbability = 0 }: CounterfactualCardsProps) {
  if (!counterfactuals || counterfactuals.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        Focus on the top factors highlighted above to improve your profile.
      </p>
    );
  }

  // Build recommendations sorted by impact
  const sorted = [...counterfactuals].sort((a, b) => {
    const impactA = (a.projected_approval_probability || a.estimated_impact || 50) - currentApprovalProbability;
    const impactB = (b.projected_approval_probability || b.estimated_impact || 50) - currentApprovalProbability;
    return impactB - impactA;
  });

  const recommendations = sorted.map((cf, i) => buildRecommendation(cf, currentApprovalProbability, i + 1));

  return (
    <div className="space-y-5">
      {recommendations.map((rec, i) => (
        <div
          key={i}
          className={`rounded-lg border p-5 ${i < 3 ? "border-primary/30 bg-primary/5" : "border-border bg-card"}`}
        >
          {/* Header */}
          <div className="flex items-start justify-between mb-3">
            <div className="flex items-center gap-2">
              <span className="text-2xl">{rec.icon}</span>
              <h4 className="text-sm font-bold text-foreground">{rec.title}</h4>
            </div>
            <span className={`shrink-0 rounded-full px-2.5 py-0.5 text-[10px] font-bold ${
              i === 0 ? "bg-red-100 text-red-700" :
              i === 1 ? "bg-orange-100 text-orange-700" :
              i === 2 ? "bg-yellow-100 text-yellow-700" :
              "bg-muted text-muted-foreground"
            }`}>
              Priority {rec.priority}
            </span>
          </div>

          {/* Recommendation */}
          <p className="text-sm font-semibold text-foreground mb-2">
            {rec.recommendation}
          </p>

          {/* Action Plan */}
          <div className="mb-3 rounded-md bg-muted/50 p-3">
            <p className="text-[10px] font-bold uppercase tracking-wide text-muted-foreground mb-1.5">Action Plan</p>
            <ul className="space-y-1">
              {rec.actionPlan.slice(0, 4).map((step, j) => (
                <li key={j} className="flex items-start gap-2 text-xs text-foreground">
                  <span className="text-primary mt-0.5">•</span>
                  <span>{step}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* Why it matters */}
          <p className="text-xs text-muted-foreground mb-1">
            <span className="font-semibold">Why it matters:</span> {rec.whyItMatters}
          </p>

          {/* Potential outcome */}
          <p className="text-xs font-semibold text-primary">
            {rec.potentialOutcome}
          </p>
        </div>
      ))}
    </div>
  );
}
