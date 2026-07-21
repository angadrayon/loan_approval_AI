"use client";

import { useEffect, useState } from "react";
import { apiClient, ApiError } from "@/lib/api-client";

/**
 * Officer Risk Analytics Page — model performance comparison.
 *
 * Displays AUC-ROC, F1 Score, KS Statistic for XGBoost and Random Forest.
 * Requirements: 6.1, 6.2, 6.3, 6.4, 6.5
 */

interface ModelMetrics {
  auc_roc: number;
  f1_score: number;
  ks_statistic: number;
}

interface ModelStats {
  xgboost: ModelMetrics;
  random_forest: ModelMetrics;
}

export default function AnalyticsPage() {
  const [stats, setStats] = useState<ModelStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetch() {
      try {
        const result = await apiClient.getModelStats();
        setStats(result as unknown as ModelStats);
      } catch (err) {
        setError(err instanceof ApiError ? err.detail : "Failed to load");
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

  if (error || !stats) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-8 text-center">
        <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-6">
          <p className="text-sm text-destructive">{error || "Metrics unavailable"}</p>
        </div>
      </div>
    );
  }

  const rows: { name: string; key: keyof ModelMetrics }[] = [
    { name: "AUC-ROC", key: "auc_roc" },
    { name: "F1 Score", key: "f1_score" },
    { name: "KS Statistic", key: "ks_statistic" },
  ];

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <h1 className="mb-2 text-2xl font-bold text-foreground">Risk Analytics</h1>
      <p className="mb-6 text-sm text-muted-foreground">
        Model performance metrics computed on the test dataset (80/20 split).
      </p>

      <div className="overflow-x-auto rounded-lg border border-border">
        <table className="w-full text-sm">
          <thead className="bg-muted/50">
            <tr>
              <th className="px-6 py-4 text-left font-medium text-muted-foreground">Metric</th>
              <th className="px-6 py-4 text-center font-medium text-muted-foreground">XGBoost (Primary)</th>
              <th className="px-6 py-4 text-center font-medium text-muted-foreground">Random Forest</th>
              <th className="px-6 py-4 text-center font-medium text-muted-foreground">Best</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {rows.map(({ name, key }) => {
              const xgb = stats.xgboost[key];
              const rf = stats.random_forest[key];
              const best = xgb >= rf ? "XGBoost" : "Random Forest";
              return (
                <tr key={key} className="hover:bg-accent/30">
                  <td className="px-6 py-4 font-medium text-foreground">{name}</td>
                  <td className={`px-6 py-4 text-center font-mono ${best === "XGBoost" ? "text-primary font-bold" : ""}`}>{xgb.toFixed(4)}</td>
                  <td className={`px-6 py-4 text-center font-mono ${best === "Random Forest" ? "text-primary font-bold" : ""}`}>{rf.toFixed(4)}</td>
                  <td className="px-6 py-4 text-center text-xs font-medium text-muted-foreground">{best}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="mt-6 rounded-lg border border-border bg-card p-4">
        <p className="text-xs text-muted-foreground">
          The XGBoost model is used for all final lending decisions. Random Forest provides a comparison baseline.
          Metrics are refreshed each time models are retrained.
        </p>
      </div>
    </div>
  );
}
