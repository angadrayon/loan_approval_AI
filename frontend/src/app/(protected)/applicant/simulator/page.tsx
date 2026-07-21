"use client";

import { useState } from "react";
import { apiClient, ApiError } from "@/lib/api-client";
import type { LoanApplicationInput, SimulationResult } from "@/types";

/**
 * What-If Simulator Page.
 *
 * Allows applicants to modify financial inputs and instantly see
 * how changes affect approval chances without formal submission.
 *
 * Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7
 */

const INITIAL_VALUES: LoanApplicationInput = {
  age: 30,
  monthly_income: 5000,
  employment_status: "Employed",
  employment_length: 5,
  credit_score: 650,
  existing_loans: 2,
  monthly_emi: 1000,
  dti_ratio: 30,
  credit_utilization: 40,
  loan_amount_requested: 50000,
};

function getRiskColor(level: string): string {
  switch (level) {
    case "Very Low Risk": return "text-green-700";
    case "Low Risk": return "text-green-600";
    case "Moderate Risk": return "text-yellow-700";
    case "High Risk": return "text-orange-700";
    case "Very High Risk": return "text-red-700";
    default: return "text-muted-foreground";
  }
}

export default function SimulatorPage() {
  const [formData, setFormData] = useState<LoanApplicationInput>(INITIAL_VALUES);
  const [result, setResult] = useState<SimulationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleChange = (name: string, value: string) => {
    const numericFields = [
      "age", "monthly_income", "employment_length", "credit_score",
      "existing_loans", "monthly_emi", "dti_ratio", "credit_utilization",
      "loan_amount_requested",
    ];
    const parsed = numericFields.includes(name) ? (value === "" ? 0 : Number(value)) : value;
    setFormData((prev) => ({ ...prev, [name]: parsed }));
  };

  const handleSimulate = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.simulateWhatIf(formData);
      setResult(res);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.detail);
      } else {
        setError("Simulation failed. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold tracking-tight text-foreground">What-If Simulator</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Adjust your financial details to see how changes affect your approval chances. No data is saved.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Input Panel */}
        <div className="rounded-lg border border-border bg-card p-6">
          <h3 className="mb-4 text-sm font-semibold text-foreground">Adjust Values</h3>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <SimField label="Age" name="age" value={formData.age} onChange={handleChange} />
            <SimField label="Monthly Income" name="monthly_income" value={formData.monthly_income} onChange={handleChange} />
            <div className="space-y-1">
              <label className="text-xs font-medium text-muted-foreground">Employment Status</label>
              <select
                value={formData.employment_status}
                onChange={(e) => handleChange("employment_status", e.target.value)}
                className="block w-full min-h-[40px] rounded-md border border-input bg-background px-2 py-1 text-sm"
              >
                <option value="Employed">Employed</option>
                <option value="Self-Employed">Self-Employed</option>
                <option value="Unemployed">Unemployed</option>
                <option value="Retired">Retired</option>
              </select>
            </div>
            <SimField label="Employment Length (yrs)" name="employment_length" value={formData.employment_length} onChange={handleChange} />
            <SimField label="Credit Score" name="credit_score" value={formData.credit_score} onChange={handleChange} />
            <SimField label="Existing Loans" name="existing_loans" value={formData.existing_loans} onChange={handleChange} />
            <SimField label="Monthly EMI" name="monthly_emi" value={formData.monthly_emi} onChange={handleChange} />
            <SimField label="DTI Ratio (%)" name="dti_ratio" value={formData.dti_ratio} onChange={handleChange} />
            <SimField label="Credit Utilization (%)" name="credit_utilization" value={formData.credit_utilization} onChange={handleChange} />
            <SimField label="Loan Amount" name="loan_amount_requested" value={formData.loan_amount_requested} onChange={handleChange} />
          </div>

          <button
            onClick={handleSimulate}
            disabled={loading}
            className="mt-4 flex w-full min-h-[44px] items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
          >
            {loading ? (
              <span className="flex items-center gap-2">
                <span className="h-4 w-4 animate-spin rounded-full border-2 border-primary-foreground border-t-transparent" />
                Simulating...
              </span>
            ) : (
              "Simulate"
            )}
          </button>

          {error && (
            <p className="mt-3 text-xs text-destructive">{error}</p>
          )}
        </div>

        {/* Results Panel */}
        <div className="rounded-lg border border-border bg-card p-6">
          <h3 className="mb-4 text-sm font-semibold text-foreground">Simulated Results</h3>

          {!result ? (
            <div className="flex h-48 items-center justify-center text-sm text-muted-foreground">
              Adjust values and click Simulate to see results.
            </div>
          ) : (
            <div className="space-y-4">
              {/* Decision */}
              <div className={`rounded-md p-4 text-center ${result.decision === "Approved" ? "bg-green-50 border border-green-200" : "bg-red-50 border border-red-200"}`}>
                <p className={`text-2xl font-bold ${result.decision === "Approved" ? "text-green-700" : "text-red-700"}`}>
                  {result.decision}
                </p>
              </div>

              {/* Metrics */}
              <div className="grid grid-cols-2 gap-3">
                <MetricCard label="Approval Probability" value={`${result.approval_probability.toFixed(1)}%`} />
                <MetricCard label="Risk Score" value={result.risk_score.toFixed(1)} subtitle={<span className={getRiskColor(result.risk_level)}>{result.risk_level}</span>} />
                <MetricCard label="Readiness Score" value={result.loan_readiness_score.toFixed(1)} subtitle={result.readiness_category} />
                <MetricCard label="Decision Threshold" value="50%" subtitle="Approval ≥ 50%" />
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function SimField({ label, name, value, onChange }: { label: string; name: string; value: number; onChange: (n: string, v: string) => void }) {
  return (
    <div className="space-y-1">
      <label className="text-xs font-medium text-muted-foreground">{label}</label>
      <input
        type="number"
        value={value || ""}
        onChange={(e) => onChange(name, e.target.value)}
        className="block w-full min-h-[40px] rounded-md border border-input bg-background px-2 py-1 text-sm"
      />
    </div>
  );
}

function MetricCard({ label, value, subtitle }: { label: string; value: string; subtitle?: React.ReactNode }) {
  return (
    <div className="rounded-md border border-border p-3">
      <p className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className="mt-1 text-xl font-bold text-foreground">{value}</p>
      {subtitle && <p className="text-xs text-muted-foreground">{subtitle}</p>}
    </div>
  );
}
