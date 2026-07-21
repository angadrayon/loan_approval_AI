"use client";

import { LoanApplicationForm } from "@/components/forms/LoanApplicationForm";

/**
 * Loan Application Page.
 *
 * Presents the loan application form for authenticated Applicants.
 * On successful submission, redirects to the assessment result page.
 */
export default function ApplyPage() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold tracking-tight text-foreground md:text-3xl">
          New Loan Application
        </h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Fill in your financial details below to receive a credit risk assessment
          with personalized recommendations.
        </p>
      </div>

      <div className="rounded-lg border border-border bg-card p-6 shadow-sm">
        <LoanApplicationForm />
      </div>
    </div>
  );
}
