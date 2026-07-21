"use client";

/**
 * SHAP Waterfall Chart — displays feature contributions as horizontal bars.
 * Uses pure CSS (no Plotly dependency needed for this simplified version).
 * Shows direction (positive/negative), magnitude, and feature name.
 *
 * Requirements: 7.2, 7.3, 7.4, 7.5
 */

interface ShapValueItem {
  feature_name?: string;
  feature?: string;
  feature_value?: number;
  value?: number;
  shap_value: number;
  direction: string;
}

interface ShapWaterfallChartProps {
  shapValues: ShapValueItem[];
  title?: string;
  maxItems?: number;
}

const FEATURE_DISPLAY_NAMES: Record<string, string> = {
  age: "Age",
  monthly_income: "Monthly Income",
  employment_status_encoded: "Employment Status",
  employment_length: "Employment Length",
  credit_score: "Credit Score",
  existing_loans: "Existing Loans",
  monthly_emi: "Monthly EMI",
  dti_ratio: "Debt-to-Income Ratio",
  credit_utilization: "Credit Utilization",
  loan_amount_requested: "Loan Amount",
};

export function ShapWaterfallChart({
  shapValues,
  title = "Feature Contributions",
  maxItems = 10,
}: ShapWaterfallChartProps) {
  if (!shapValues || shapValues.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        Explanation data is not available.
      </p>
    );
  }

  // Sort by absolute SHAP value descending
  const sorted = [...shapValues]
    .sort((a, b) => Math.abs(b.shap_value) - Math.abs(a.shap_value))
    .slice(0, maxItems);

  const maxMagnitude = Math.max(...sorted.map((s) => Math.abs(s.shap_value)), 0.01);

  return (
    <div>
      {title && (
        <h4 className="mb-3 text-sm font-semibold text-foreground">{title}</h4>
      )}
      <div className="space-y-2">
        {sorted.map((item, i) => {
          const featureName = item.feature_name || item.feature || `Feature ${i}`;
          const displayName = FEATURE_DISPLAY_NAMES[featureName] || featureName.replace(/_/g, " ");
          const featureValue = item.feature_value ?? item.value ?? 0;
          const barWidth = (Math.abs(item.shap_value) / maxMagnitude) * 100;
          const isPositive = item.direction === "positive";
          const isTop3 = i < 3;

          return (
            <div
              key={i}
              className={`flex items-center gap-3 rounded-md px-3 py-2 ${isTop3 ? "bg-muted/70 border border-border" : ""}`}
            >
              {/* Feature name */}
              <div className="w-36 shrink-0">
                <p className="text-xs font-medium text-foreground truncate" title={displayName}>
                  {displayName}
                </p>
                <p className="text-[10px] text-muted-foreground">
                  {typeof featureValue === "number" ? featureValue.toFixed(1) : featureValue}
                </p>
              </div>

              {/* Bar */}
              <div className="flex-1 flex items-center">
                <div className="relative h-5 w-full rounded bg-muted/30">
                  <div
                    className={`absolute top-0 h-5 rounded transition-all ${
                      isPositive ? "bg-green-500/70 left-0" : "bg-red-500/70 left-0"
                    }`}
                    style={{ width: `${Math.min(barWidth, 100)}%` }}
                  />
                </div>
              </div>

              {/* Direction indicator */}
              <div className="w-16 shrink-0 text-right">
                <span
                  className={`text-xs font-medium ${
                    isPositive ? "text-green-600" : "text-red-600"
                  }`}
                >
                  {isPositive ? "↑ Helped" : "↓ Hurt"}
                </span>
              </div>
            </div>
          );
        })}
      </div>
      <p className="mt-2 text-[10px] text-muted-foreground">
        Top 3 factors are highlighted. Green = helped approval, Red = hurt approval.
      </p>
    </div>
  );
}
