"use client";

/**
 * Readiness Gauge — color-coded visual indicator for Loan Readiness Score.
 *
 * Categories:
 *   0-25:  Poor (red)
 *   26-50: Fair (orange)
 *   51-75: Good (yellow)
 *   76-100: Excellent (green)
 *
 * Requirements: 9.3
 */

interface ReadinessGaugeProps {
  score: number;
  category: string;
}

function getCategoryConfig(category: string) {
  switch (category) {
    case "Excellent":
      return { color: "bg-green-500", textColor: "text-green-700", bgColor: "bg-green-50", borderColor: "border-green-200", description: "You are well-prepared for loan approval." };
    case "Good":
      return { color: "bg-yellow-500", textColor: "text-yellow-700", bgColor: "bg-yellow-50", borderColor: "border-yellow-200", description: "Your profile is solid with minor areas for improvement." };
    case "Fair":
      return { color: "bg-orange-500", textColor: "text-orange-700", bgColor: "bg-orange-50", borderColor: "border-orange-200", description: "There are several areas that could strengthen your application." };
    case "Poor":
      return { color: "bg-red-500", textColor: "text-red-700", bgColor: "bg-red-50", borderColor: "border-red-200", description: "Significant improvements are needed before applying." };
    default:
      return { color: "bg-muted", textColor: "text-muted-foreground", bgColor: "bg-muted", borderColor: "border-border", description: "" };
  }
}

export function ReadinessGauge({ score, category }: ReadinessGaugeProps) {
  const config = getCategoryConfig(category);
  const clampedScore = Math.max(0, Math.min(100, score));

  return (
    <div className={`rounded-lg border p-4 ${config.borderColor} ${config.bgColor}`}>
      <div className="flex items-center justify-between mb-2">
        <h4 className="text-sm font-semibold text-foreground">Loan Readiness</h4>
        <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${config.textColor} ${config.bgColor} border ${config.borderColor}`}>
          {category}
        </span>
      </div>

      {/* Score display */}
      <div className="flex items-baseline gap-1 mb-3">
        <span className={`text-3xl font-bold ${config.textColor}`}>
          {clampedScore.toFixed(0)}
        </span>
        <span className="text-sm text-muted-foreground">/100</span>
      </div>

      {/* Progress bar */}
      <div className="relative h-3 w-full rounded-full bg-muted/50 overflow-hidden">
        {/* Background segments */}
        <div className="absolute inset-0 flex">
          <div className="w-1/4 bg-red-200/50" />
          <div className="w-1/4 bg-orange-200/50" />
          <div className="w-1/4 bg-yellow-200/50" />
          <div className="w-1/4 bg-green-200/50" />
        </div>
        {/* Fill */}
        <div
          className={`absolute top-0 left-0 h-full rounded-full transition-all duration-500 ${config.color}`}
          style={{ width: `${clampedScore}%` }}
        />
      </div>

      {/* Scale labels */}
      <div className="mt-1 flex justify-between text-[10px] text-muted-foreground">
        <span>Poor</span>
        <span>Fair</span>
        <span>Good</span>
        <span>Excellent</span>
      </div>

      {/* Description */}
      <p className="mt-3 text-xs text-muted-foreground">{config.description}</p>
    </div>
  );
}
