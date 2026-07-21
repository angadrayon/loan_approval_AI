"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { apiClient, ApiError } from "@/lib/api-client";
import { ShapWaterfallChart } from "@/components/charts/ShapWaterfallChart";

/**
 * Officer Application Detail Page.
 *
 * Shows complete application details, prediction results, SHAP explanations,
 * and counterfactual recommendations for a specific application.
 *
 * Requirements: 7.3, 8.6, 12.4, 15.3
 */

interface AppDetail {
  application: Record<string, unknown>;
  prediction: {
    approval_probability: number;
    risk_score: number;
    risk_level: string;
    default_probability: number;
    decision: string;
    loan_readiness_score: number;
    readiness_category: string;
    rf_approval_probability: number;
  } | null;
  shap_values: Array<{ feature_name: string; feature_value: number; shap_value: number; direction: string }>;
  counterfactuals: Array<{ feature_name: string; current_value: number; recommended_value: number; estimated_impact: number }>;
}

export default function OfficerApplicationDetailPage() {
  const params = useParams();
  const appId = params.id as string;

  const [data, setData] = useState<AppDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetch() {
      try {
        const result = await apiClient.getApplicationById(appId);
        setData(result as unknown as AppDetail);
      } catch (err) {
        setError(err instanceof ApiError ? err.detail : "Failed to load");
      } finally {
        setLoading(false);
      }
    }
    if (appId) fetch();
  }, [appId]);

  if (loading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-8 text-center">
        <p className="text-destructive">{error || "Not found"}</p>
        <Link href="/officer/applications" className="mt-4 inline-block text-sm text-primary hover:underline">← Back to list</Link>
      </div>
    );
  }

  const app = data.application;
  const pred = data.prediction;

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-foreground">Application Review</h1>
        <Link href="/officer/applications" className="text-sm text-primary hover:underline">← Back to list</Link>
      </div>

      {/* Application Inputs */}
      <div className="mb-6 rounded-lg border border-border bg-card p-6">
        <h3 className="mb-3 text-sm font-semibold text-foreground">Applicant Information</h3>
        <div className="grid grid-cols-2 gap-3 text-sm md:grid-cols-3 lg:grid-cols-5">
          <InfoItem label="Age" value={String(app.age ?? "—")} />
          <InfoItem label="Income" value={`$${Number(app.monthly_income || 0).toLocaleString()}`} />
          <InfoItem label="Employment" value={String(app.employment_status ?? "—")} />
          <InfoItem label="Emp. Length" value={`${app.employment_length ?? "—"} yrs`} />
          <InfoItem label="Credit Score" value={String(app.credit_score ?? "—")} />
          <InfoItem label="Existing Loans" value={String(app.existing_loans ?? "—")} />
          <InfoItem label="Monthly EMI" value={`$${Number(app.monthly_emi || 0).toLocaleString()}`} />
          <InfoItem label="DTI Ratio" value={`${app.dti_ratio ?? "—"}%`} />
          <InfoItem label="Credit Util." value={`${app.credit_utilization ?? "—"}%`} />
          <InfoItem label="Loan Amount" value={`$${Number(app.loan_amount_requested || 0).toLocaleString()}`} />
        </div>
      </div>

      {/* Prediction Results */}
      {pred && (
        <>
          <div className="mb-6 grid grid-cols-2 gap-4 md:grid-cols-4">
            <MetricCard label="Decision" value={pred.decision} highlight={pred.decision === "Approved" ? "green" : "red"} />
            <MetricCard label="Approval %" value={`${pred.approval_probability.toFixed(1)}%`} />
            <MetricCard label="Risk Score" value={pred.risk_score.toFixed(1)} subtitle={pred.risk_level} />
            <MetricCard label="Readiness" value={pred.loan_readiness_score.toFixed(1)} subtitle={pred.readiness_category} />
          </div>

          {/* SHAP Chart */}
          {data.shap_values.length > 0 && (
            <div className="mb-6 rounded-lg border border-border bg-card p-6">
              <h3 className="mb-3 text-sm font-semibold text-foreground">SHAP Feature Contributions</h3>
              <ShapWaterfallChart shapValues={data.shap_values} title="" />
            </div>
          )}

          {/* Counterfactuals */}
          {data.counterfactuals.length > 0 && (
            <div className="mb-6 rounded-lg border border-border bg-card p-6">
              <h3 className="mb-3 text-sm font-semibold text-foreground">Counterfactual Recommendations</h3>
              <div className="space-y-2">
                {data.counterfactuals.map((cf, i) => (
                  <div key={i} className="flex items-center justify-between rounded-md border border-border px-3 py-2 text-sm">
                    <span className="text-foreground">{cf.feature_name.replace(/_/g, " ")}</span>
                    <span className="text-muted-foreground">{cf.current_value.toFixed(1)} → <strong className="text-primary">{cf.recommended_value.toFixed(1)}</strong></span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function InfoItem({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="font-medium text-foreground">{value}</p>
    </div>
  );
}

function MetricCard({ label, value, subtitle, highlight }: { label: string; value: string; subtitle?: string; highlight?: "green" | "red" }) {
  const hlClass = highlight === "green" ? "text-green-700" : highlight === "red" ? "text-red-700" : "text-foreground";
  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className={`mt-1 text-xl font-bold ${hlClass}`}>{value}</p>
      {subtitle && <p className="text-xs text-muted-foreground">{subtitle}</p>}
    </div>
  );
}
