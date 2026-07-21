"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { apiClient, ApiError } from "@/lib/api-client";
import type { LoanApplicationInput, EmploymentStatus } from "@/types";

/**
 * Loan Application Form Component.
 *
 * Collects all 10 financial input fields, validates against Requirement 4 rules,
 * submits to POST /api/v1/applications via the API client, and navigates
 * to the assessment result page on success.
 *
 * Requirements: 4.1, 4.2, 4.3–4.11, 4.12, 17.1, 19.5
 */

interface FieldError {
  [key: string]: string | null;
}

const EMPLOYMENT_OPTIONS: EmploymentStatus[] = [
  "Employed",
  "Self-Employed",
  "Unemployed",
  "Retired",
];

function validateField(name: string, value: number | string, allValues: Partial<LoanApplicationInput>): string | null {
  switch (name) {
    case "age": {
      const v = Number(value);
      if (!v || v < 18 || v > 100) return "Age must be between 18 and 100";
      if (!Number.isInteger(v)) return "Age must be a whole number";
      return null;
    }
    case "monthly_income": {
      const v = Number(value);
      if (!v || v <= 0) return "Monthly income must be greater than 0";
      if (v > 10_000_000) return "Monthly income cannot exceed 10,000,000";
      return null;
    }
    case "employment_status":
      if (!EMPLOYMENT_OPTIONS.includes(value as EmploymentStatus))
        return "Please select an employment status";
      return null;
    case "employment_length": {
      const v = Number(value);
      if (v < 0 || v > 50) return "Employment length must be 0–50 years";
      return null;
    }
    case "credit_score": {
      const v = Number(value);
      if (!v || v < 300 || v > 850) return "Credit score must be 300–850";
      if (!Number.isInteger(v)) return "Credit score must be a whole number";
      return null;
    }
    case "existing_loans": {
      const v = Number(value);
      if (v < 0 || v > 50) return "Existing loans must be 0–50";
      if (!Number.isInteger(v)) return "Must be a whole number";
      return null;
    }
    case "monthly_emi": {
      const v = Number(value);
      if (v < 0) return "Monthly EMI cannot be negative";
      const income = Number(allValues.monthly_income) || 0;
      if (income > 0 && v > income) return "Monthly EMI cannot exceed monthly income";
      return null;
    }
    case "dti_ratio": {
      const v = Number(value);
      if (v < 0 || v > 100) return "DTI ratio must be 0–100%";
      return null;
    }
    case "credit_utilization": {
      const v = Number(value);
      if (v < 0 || v > 100) return "Credit utilization must be 0–100%";
      return null;
    }
    case "loan_amount_requested": {
      const v = Number(value);
      if (!v || v <= 0) return "Loan amount must be greater than 0";
      if (v > 10_000_000) return "Loan amount cannot exceed 10,000,000";
      return null;
    }
    default:
      return null;
  }
}

export function LoanApplicationForm() {
  const router = useRouter();

  const [formData, setFormData] = useState<LoanApplicationInput>({
    age: 0,
    monthly_income: 0,
    employment_status: "Employed",
    employment_length: 0,
    credit_score: 0,
    existing_loans: 0,
    monthly_emi: 0,
    dti_ratio: 0,
    credit_utilization: 0,
    loan_amount_requested: 0,
  });

  const [errors, setErrors] = useState<FieldError>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleChange = (name: string, value: string) => {
    const numericFields = [
      "age", "monthly_income", "employment_length", "credit_score",
      "existing_loans", "monthly_emi", "dti_ratio", "credit_utilization",
      "loan_amount_requested",
    ];

    let parsedValue: string | number = value;
    if (numericFields.includes(name)) {
      parsedValue = value === "" ? 0 : Number(value);
    }

    const newData = { ...formData, [name]: parsedValue };
    setFormData(newData);

    // Clear error on change if previously shown
    if (errors[name]) {
      const error = validateField(name, parsedValue, newData);
      setErrors((prev) => ({ ...prev, [name]: error }));
    }
  };

  const handleBlur = (name: string) => {
    const value = formData[name as keyof LoanApplicationInput];
    const error = validateField(name, value as number | string, formData);
    setErrors((prev) => ({ ...prev, [name]: error }));
  };

  const validateAll = (): boolean => {
    const newErrors: FieldError = {};
    let hasError = false;

    for (const key of Object.keys(formData) as (keyof LoanApplicationInput)[]) {
      const error = validateField(key, formData[key] as number | string, formData);
      newErrors[key] = error;
      if (error) hasError = true;
    }

    setErrors(newErrors);
    return !hasError;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);

    if (!validateAll()) return;

    setIsSubmitting(true);

    try {
      const result = await apiClient.submitApplication(formData);
      router.push(`/applicant/assessment/${result.application_id}`);
    } catch (error) {
      if (error instanceof ApiError) {
        if (error.status === 401) {
          setFormError("Session expired. Please log out and log back in.");
        } else if (error.status === 422) {
          setFormError("Please check your input values and try again.");
        } else if (error.status === 503) {
          setFormError("Prediction service is temporarily unavailable. Please try again later.");
        } else if (error.status === 504) {
          setFormError("Prediction timed out. Please try again.");
        } else {
          setFormError(error.detail);
        }
      } else {
        setFormError("An unexpected error occurred. Please try again.");
      }
      setIsSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} noValidate className="space-y-6">
      {formError && (
        <div className="rounded-md border border-destructive/50 bg-destructive/10 p-3 text-sm text-destructive">
          {formError}
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {/* Age */}
        <FormField
          label="Age"
          name="age"
          type="number"
          value={formData.age || ""}
          error={errors.age}
          placeholder="18–100"
          onChange={handleChange}
          onBlur={handleBlur}
        />

        {/* Monthly Income */}
        <FormField
          label="Monthly Income"
          name="monthly_income"
          type="number"
          value={formData.monthly_income || ""}
          error={errors.monthly_income}
          placeholder="e.g. 5000"
          onChange={handleChange}
          onBlur={handleBlur}
        />

        {/* Employment Status */}
        <div className="space-y-1.5">
          <label htmlFor="employment_status" className="block text-sm font-medium text-foreground">
            Employment Status
          </label>
          <select
            id="employment_status"
            value={formData.employment_status}
            onChange={(e) => handleChange("employment_status", e.target.value)}
            onBlur={() => handleBlur("employment_status")}
            className="block w-full min-h-[44px] rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-1"
          >
            {EMPLOYMENT_OPTIONS.map((opt) => (
              <option key={opt} value={opt}>{opt}</option>
            ))}
          </select>
          {errors.employment_status && (
            <p className="text-xs text-destructive" role="alert">{errors.employment_status}</p>
          )}
        </div>

        {/* Employment Length */}
        <FormField
          label="Employment Length (years)"
          name="employment_length"
          type="number"
          value={formData.employment_length || ""}
          error={errors.employment_length}
          placeholder="0–50"
          onChange={handleChange}
          onBlur={handleBlur}
        />

        {/* Credit Score */}
        <FormField
          label="Credit Score"
          name="credit_score"
          type="number"
          value={formData.credit_score || ""}
          error={errors.credit_score}
          placeholder="300–850"
          onChange={handleChange}
          onBlur={handleBlur}
        />

        {/* Existing Loans */}
        <FormField
          label="Existing Loans"
          name="existing_loans"
          type="number"
          value={formData.existing_loans || ""}
          error={errors.existing_loans}
          placeholder="0–50"
          onChange={handleChange}
          onBlur={handleBlur}
        />

        {/* Monthly EMI */}
        <FormField
          label="Monthly EMI"
          name="monthly_emi"
          type="number"
          value={formData.monthly_emi || ""}
          error={errors.monthly_emi}
          placeholder="Current monthly payments"
          onChange={handleChange}
          onBlur={handleBlur}
        />

        {/* DTI Ratio */}
        <FormField
          label="DTI Ratio (%)"
          name="dti_ratio"
          type="number"
          value={formData.dti_ratio || ""}
          error={errors.dti_ratio}
          placeholder="0–100"
          onChange={handleChange}
          onBlur={handleBlur}
        />

        {/* Credit Utilization */}
        <FormField
          label="Credit Utilization (%)"
          name="credit_utilization"
          type="number"
          value={formData.credit_utilization || ""}
          error={errors.credit_utilization}
          placeholder="0–100"
          onChange={handleChange}
          onBlur={handleBlur}
        />

        {/* Loan Amount Requested */}
        <FormField
          label="Loan Amount Requested"
          name="loan_amount_requested"
          type="number"
          value={formData.loan_amount_requested || ""}
          error={errors.loan_amount_requested}
          placeholder="e.g. 50000"
          onChange={handleChange}
          onBlur={handleBlur}
        />
      </div>

      {/* Submit Button */}
      <button
        type="submit"
        disabled={isSubmitting}
        className="flex w-full min-h-[44px] items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {isSubmitting ? (
          <span className="flex items-center gap-2">
            <span className="h-4 w-4 animate-spin rounded-full border-2 border-primary-foreground border-t-transparent" />
            Analyzing your application...
          </span>
        ) : (
          "Submit Application"
        )}
      </button>
    </form>
  );
}

// ============================================================
// Reusable Form Field Component
// ============================================================

interface FormFieldProps {
  label: string;
  name: string;
  type: string;
  value: string | number;
  error: string | null | undefined;
  placeholder?: string;
  onChange: (name: string, value: string) => void;
  onBlur: (name: string) => void;
}

function FormField({ label, name, type, value, error, placeholder, onChange, onBlur }: FormFieldProps) {
  return (
    <div className="space-y-1.5">
      <label htmlFor={name} className="block text-sm font-medium text-foreground">
        {label}
      </label>
      <input
        id={name}
        name={name}
        type={type}
        value={value}
        onChange={(e) => onChange(name, e.target.value)}
        onBlur={() => onBlur(name)}
        placeholder={placeholder}
        aria-invalid={!!error}
        aria-describedby={error ? `${name}-error` : undefined}
        className={`block w-full min-h-[44px] rounded-md border px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-1 ${
          error ? "border-destructive focus:ring-destructive" : "border-input"
        }`}
      />
      {error && (
        <p id={`${name}-error`} className="text-xs text-destructive" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
