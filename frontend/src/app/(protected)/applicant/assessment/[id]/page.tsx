"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { apiClient, ApiError } from "@/lib/api-client";
import { ShapWaterfallChart } from "@/components/charts/ShapWaterfallChart";
import { ReadinessGauge } from "@/components/charts/ReadinessGauge";
import { CounterfactualCards } from "@/components/explanations/CounterfactualCards";

/**
 * Assessment Detail Page — integrated with SHAP chart and Readiness Gauge.
 *
 * Requirements: 5.3, 7.2, 8.2, 8.5, 9.3, 13.1, 14.3, 14.4, 20.4, 20.5
 */

interface AssessmentData {
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
    created_at: string;
  } | null;
  shap_values: Array<{ feature_name: string; feature_value: number; shap_value: number; direction: string }>;
  counterfactuals: Array<{ feature_name: string; current_value: number; recommended_value: number; estimated_impact: number }>;
}

function getDecisionColor(decision: string): string {
  return decision === "Approved" ? "text-green-600 bg-green-50 border-green-200" : "text-red-600 bg-red-50 border-red-200";
}

function getRiskColor(level: string): string {
  switch (level) {
    case "Very Low Risk": return "text-green-700 bg-green-100";
    case "Low Risk": return "text-green-600 bg-green-50";
    case "Moderate Risk": return "text-yellow-700 bg-yellow-100";
    case "High Risk": return "text-orange-700 bg-orange-100";
    case "Very High Risk": return "text-red-700 bg-red-100";
    default: return "text-muted-foreground bg-muted";
  }
}

export default function AssessmentDetailPage() {
  const params = useParams();
  const applicationId = params.id as string;
  const [data, setData] = useState<AssessmentData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [downloadingPdf, setDownloadingPdf] = useState(false);
  const [pdfError, setPdfError] = useState<string | null>(null);

  async function handleDownloadPdf() {
    setDownloadingPdf(true);
    setPdfError(null);
    try {
      const blob = await apiClient.downloadReport(applicationId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `assessment_${applicationId.slice(0, 8)}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      setPdfError(err instanceof ApiError ? err.detail : "Failed to download report");
    } finally {
      setDownloadingPdf(false);
    }
  }

  useEffect(() => {
    async function fetchAssessment() {
      try {
        const result = await apiClient.getApplicationById(applicationId);
        setData(result as unknown as AssessmentData);
      } catch (err) {
        setError(err instanceof ApiError ? err.detail : "Failed to load assessment data");
      } finally {
        setLoading(false);
      }
    }
    if (applicationId) fetchAssessment();
  }, [applicationId]);

  if (loading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="h-8 w-8 mx-auto animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-8 text-center">
        <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-6">
          <p className="text-sm text-destructive">{error || "Assessment not found"}</p>
          <Link href="/applicant/dashboard" className="mt-4 inline-block text-sm text-primary hover:underline">Return to Dashboard</Link>
        </div>
      </div>
    );
  }

  const prediction = data.prediction;
  if (!prediction) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-8 text-center">
        <p className="text-muted-foreground">Your application is being processed.</p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">Assessment Result</h1>
          <p className="text-xs text-muted-foreground">ID: {applicationId.slice(0, 8)}...</p>
        </div>
        <Link href="/applicant/dashboard" className="text-sm text-primary hover:underline">← Dashboard</Link>
      </div>

      {/* Decision Banner */}
      <div className={`mb-6 rounded-lg border p-6 text-center ${getDecisionColor(prediction.decision)}`}>
        <p className="text-sm font-medium uppercase tracking-wide opacity-75">Decision</p>
        <h2 className="mt-1 text-3xl font-bold">{prediction.decision}</h2>
        <p className="mt-2 text-sm opacity-75">
          {prediction.decision === "Approved"
            ? "Your application meets the approval criteria."
            : "See recommendations below to improve your chances."}
        </p>
      </div>

      {/* Metrics Grid */}
      <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <div className="rounded-lg border border-border bg-card p-4">
          <p className="text-xs font-medium uppercase text-muted-foreground">Approval Probability</p>
          <p className="mt-1 text-2xl font-bold text-foreground">{prediction.approval_probability.toFixed(1)}%</p>
        </div>
        <div className="rounded-lg border border-border bg-card p-4">
          <p className="text-xs font-medium uppercase text-muted-foreground">Risk Score</p>
          <p className="mt-1 text-2xl font-bold text-foreground">{prediction.risk_score.toFixed(1)}</p>
          <span className={`mt-1 inline-block rounded-full px-2 py-0.5 text-xs font-medium ${getRiskColor(prediction.risk_level)}`}>{prediction.risk_level}</span>
        </div>
        <div className="rounded-lg border border-border bg-card p-4">
          <p className="text-xs font-medium uppercase text-muted-foreground">RF Comparison</p>
          <p className="mt-1 text-2xl font-bold text-foreground">{prediction.rf_approval_probability.toFixed(1)}%</p>
          <p className="text-xs text-muted-foreground">Random Forest model</p>
        </div>
      </div>

      {/* Readiness Gauge */}
      <div className="mb-6">
        <ReadinessGauge score={prediction.loan_readiness_score} category={prediction.readiness_category} />
      </div>

      {/* SHAP Waterfall Chart */}
      {data.shap_values && data.shap_values.length > 0 && (
        <div className="mb-6 rounded-lg border border-border bg-card p-6">
          <h3 className="mb-1 text-lg font-semibold text-card-foreground">What Influenced This Decision</h3>
          <p className="mb-4 text-xs text-muted-foreground">Features sorted by impact on your approval decision.</p>
          <ShapWaterfallChart shapValues={data.shap_values} title="" />
        </div>
      )}

      {/* Counterfactual Recommendations (Rejected only) */}
      {prediction.decision === "Rejected" && (
        <div className="mb-6 rounded-lg border border-border bg-card p-6">
          <h3 className="mb-1 text-lg font-semibold text-card-foreground">How to Improve Your Chances</h3>
          <p className="mb-4 text-xs text-muted-foreground">Personalized recommendations based on your application.</p>
          <CounterfactualCards
            counterfactuals={data.counterfactuals}
            currentApprovalProbability={prediction.approval_probability}
          />
        </div>
      )}

      {/* Actions */}
      <div className="flex flex-wrap gap-3">
        <button
          onClick={handleDownloadPdf}
          disabled={downloadingPdf}
          className="inline-flex min-h-[44px] items-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
        >
          {downloadingPdf ? "Generating PDF..." : "Download PDF Report"}
        </button>
        <Link href="/applicant/apply" className="inline-flex min-h-[44px] items-center rounded-md border border-border bg-card px-4 py-2 text-sm font-medium hover:bg-accent">New Assessment</Link>
        <Link href="/applicant/history" className="inline-flex min-h-[44px] items-center rounded-md border border-border bg-card px-4 py-2 text-sm font-medium hover:bg-accent">View History</Link>
        <Link href="/applicant/simulator" className="inline-flex min-h-[44px] items-center rounded-md border border-border bg-card px-4 py-2 text-sm font-medium hover:bg-accent">What-If Simulator</Link>
      </div>
      {pdfError && <p className="mt-2 text-xs text-destructive">{pdfError}</p>}
    </div>
  );
}
