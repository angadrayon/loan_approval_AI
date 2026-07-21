"use client";

import { useEffect, useState } from "react";
import { apiClient, ApiError } from "@/lib/api-client";

/**
 * Admin Fairness Monitoring Page.
 *
 * Displays Demographic Parity, Equalized Odds, proxy bias correlations,
 * and insufficient data notices.
 *
 * Requirements: 11.1, 11.2, 11.3, 11.4, 11.5
 */

interface FairnessData {
  demographic_parity_diff: number;
  equalized_odds_diff: number;
  proxy_correlations: Record<string, number>;
  prediction_count: number;
  insufficient_data: boolean;
  computed_at: string;
}

const THRESHOLD = 0.1;

export default function FairnessPage() {
  const [data, setData] = useState<FairnessData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetch() {
      try {
        const result = await apiClient.getFairnessMetrics();
        setData(result as unknown as FairnessData);
      } catch (err) {
        if (err instanceof ApiError && err.status === 404) {
          // No metrics computed yet
          setData(null);
        } else {
          setError(err instanceof ApiError ? err.detail : "Failed to load fairness metrics");
        }
      } finally {
        setLoading(false);
      }
    }
    fetch();
  }, []);

  if (loading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <h1 className="mb-2 text-2xl font-bold text-foreground">Fairness Monitoring</h1>
      <p className="mb-6 text-sm text-muted-foreground">
        Monitor bias metrics to ensure fair lending decisions. Threshold: {THRESHOLD} for both metrics.
      </p>

      {error && (
        <div className="mb-6 rounded-lg border border-destructive/50 bg-destructive/10 p-4">
          <p className="text-sm text-destructive">{error}</p>
        </div>
      )}

      {!data ? (
        <div className="rounded-lg border border-border bg-card p-8 text-center">
          <p className="text-lg font-medium text-foreground">No Fairness Data Available</p>
          <p className="mt-2 text-sm text-muted-foreground">
            Fairness metrics will be computed once sufficient predictions exist in the system.
            At least 30 predictions are required for reliable metrics.
          </p>
        </div>
      ) : (
        <>
          {/* Insufficient data warning */}
          {data.insufficient_data && (
            <div className="mb-6 rounded-lg border border-yellow-200 bg-yellow-50 p-4">
              <p className="text-sm font-medium text-yellow-800">
                ⚠️ Insufficient Data — Only {data.prediction_count} predictions exist.
                At least 30 are needed for reliable fairness metrics.
              </p>
            </div>
          )}

          {/* Metrics Cards */}
          <div className="mb-6 grid grid-cols-1 gap-4 md:grid-cols-2">
            <MetricCard
              title="Demographic Parity Difference"
              value={data.demographic_parity_diff}
              threshold={THRESHOLD}
            />
            <MetricCard
              title="Equalized Odds Difference"
              value={data.equalized_odds_diff}
              threshold={THRESHOLD}
            />
          </div>

          {/* Proxy Bias Correlations */}
          <div className="mb-6 rounded-lg border border-border bg-card p-6">
            <h3 className="mb-3 text-sm font-semibold text-foreground">Proxy Bias Detection</h3>
            <p className="mb-3 text-xs text-muted-foreground">
              Pearson correlations between protected attributes and input features. Flagged if |r| &gt; 0.7.
            </p>
            {Object.keys(data.proxy_correlations).length === 0 ? (
              <p className="text-sm text-muted-foreground">No proxy correlations detected.</p>
            ) : (
              <div className="space-y-2">
                {Object.entries(data.proxy_correlations).map(([feature, corr]) => {
                  const flagged = Math.abs(corr) > 0.7;
                  return (
                    <div key={feature} className={`flex items-center justify-between rounded-md px-3 py-2 ${flagged ? "bg-red-50 border border-red-200" : "bg-muted/30"}`}>
                      <span className="text-sm text-foreground">{feature.replace(/_/g, " ")}</span>
                      <span className={`text-sm font-mono font-medium ${flagged ? "text-red-700" : "text-foreground"}`}>
                        r = {corr.toFixed(4)} {flagged && "⚠️"}
                      </span>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Metadata */}
          <div className="text-xs text-muted-foreground">
            <p>Predictions analyzed: {data.prediction_count}</p>
            <p>Last computed: {new Date(data.computed_at).toLocaleString()}</p>
          </div>
        </>
      )}
    </div>
  );
}

function MetricCard({ title, value, threshold }: { title: string; value: number; threshold: number }) {
  const withinThreshold = Math.abs(value) <= threshold;
  return (
    <div className={`rounded-lg border p-6 ${withinThreshold ? "border-green-200 bg-green-50" : "border-red-200 bg-red-50"}`}>
      <div className="flex items-center justify-between mb-2">
        <h4 className="text-sm font-medium text-foreground">{title}</h4>
        <span className={`h-3 w-3 rounded-full ${withinThreshold ? "bg-green-500" : "bg-red-500"}`} />
      </div>
      <p className={`text-2xl font-bold ${withinThreshold ? "text-green-700" : "text-red-700"}`}>
        {value.toFixed(4)}
      </p>
      <p className="mt-1 text-xs text-muted-foreground">
        Threshold: ≤ {threshold} · {withinThreshold ? "Within acceptable range" : "Exceeds threshold — action needed"}
      </p>
    </div>
  );
}
