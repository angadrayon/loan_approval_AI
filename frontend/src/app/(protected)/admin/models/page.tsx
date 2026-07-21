"use client";

import { useEffect, useState } from "react";
import { apiClient, ApiError } from "@/lib/api-client";

/**
 * Model Statistics Page — side-by-side comparison of XGBoost and Random Forest.
 *
 * Displays AUC-ROC, F1 Score, and KS Statistic for both models.
 * Requirements: 6.1, 6.2, 6.3, 6.4, 6.5
 */

interface ModelMetrics {
  auc_roc: number;
  f1_score: number;
  ks_statistic: number;
  optimal_threshold?: number;
}

interface ModelStats {
  xgboost: ModelMetrics;
  random_forest: ModelMetrics;
}

export default function ModelsPage() {
  const [stats, setStats] = useState<ModelStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetch() {
      try {
        const result = await apiClient.getModelStats();
        setStats(result as unknown as ModelStats);
      } catch (err) {
        setError(err instanceof ApiError ? err.detail : "Failed to load model statistics");
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

  const metrics: { name: string; key: keyof ModelMetrics }[] = [
    { name: "AUC-ROC", key: "auc_roc" },
    { name: "F1 Score", key: "f1_score" },
    { name: "KS Statistic", key: "ks_statistic" },
  ];

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <h1 className="mb-6 text-2xl font-bold text-foreground">Model Performance Comparison</h1>
      <p className="mb-6 text-sm text-muted-foreground">
        Side-by-side comparison of XGBoost (primary) and Random Forest (secondary) models
        evaluated on the test dataset.
      </p>

      <div className="overflow-x-auto rounded-lg border border-border">
        <table className="w-full text-sm">
          <thead className="bg-muted/50">
            <tr>
              <th className="px-6 py-4 text-left font-medium text-muted-foreground">Metric</th>
              <th className="px-6 py-4 text-center font-medium text-muted-foreground">XGBoost</th>
              <th className="px-6 py-4 text-center font-medium text-muted-foreground">Random Forest</th>
              <th className="px-6 py-4 text-center font-medium text-muted-foreground">Winner</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {metrics.map(({ name, key }) => {
              const xgb = stats.xgboost[key] as number;
              const rf = stats.random_forest[key] as number;
              const winner = xgb > rf ? "XGBoost" : xgb < rf ? "Random Forest" : "Tie";

              return (
                <tr key={key} className="hover:bg-accent/30">
                  <td className="px-6 py-4 font-medium text-foreground">{name}</td>
                  <td className={`px-6 py-4 text-center font-mono ${winner === "XGBoost" ? "text-primary font-bold" : "text-foreground"}`}>
                    {xgb.toFixed(4)}
                  </td>
                  <td className={`px-6 py-4 text-center font-mono ${winner === "Random Forest" ? "text-primary font-bold" : "text-foreground"}`}>
                    {rf.toFixed(4)}
                  </td>
                  <td className="px-6 py-4 text-center">
                    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                      winner === "XGBoost" ? "bg-primary/10 text-primary" :
                      winner === "Random Forest" ? "bg-orange-100 text-orange-700" :
                      "bg-muted text-muted-foreground"
                    }`}>
                      {winner}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-2">
        <div className="rounded-lg border border-border bg-card p-4">
          <h4 className="text-sm font-semibold text-foreground">XGBoost (Primary)</h4>
          <p className="mt-1 text-xs text-muted-foreground">
            Hyperparameter-tuned via Optuna. Used for final decisions.
          </p>
        </div>
        <div className="rounded-lg border border-border bg-card p-4">
          <h4 className="text-sm font-semibold text-foreground">Random Forest (Secondary)</h4>
          <p className="mt-1 text-xs text-muted-foreground">
            Comparison model. Provides a second opinion on predictions.
          </p>
        </div>
      </div>
    </div>
  );
}
