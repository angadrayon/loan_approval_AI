"use client";

import Link from "next/link";

/**
 * Bank Officer Dashboard — central hub for application review.
 *
 * Provides navigation to: Application Review, Risk Analytics,
 * Explainability Dashboard, and Audit View.
 *
 * Requirement 15.1
 */
export default function OfficerDashboard() {
  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold tracking-tight text-foreground md:text-3xl">
          Officer Dashboard
        </h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Review loan applications and monitor risk analytics.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <Link
          href="/officer/applications"
          className="group rounded-lg border border-border bg-card p-6 shadow-sm transition-colors hover:border-primary/50 hover:bg-accent/50"
        >
          <h3 className="text-lg font-semibold text-card-foreground group-hover:text-primary">
            Application Review
          </h3>
          <p className="mt-2 text-sm text-muted-foreground">
            Review submitted loan applications with full prediction details.
          </p>
        </Link>

        <Link
          href="/officer/analytics"
          className="group rounded-lg border border-border bg-card p-6 shadow-sm transition-colors hover:border-primary/50 hover:bg-accent/50"
        >
          <h3 className="text-lg font-semibold text-card-foreground group-hover:text-primary">
            Risk Analytics
          </h3>
          <p className="mt-2 text-sm text-muted-foreground">
            View model performance metrics and risk distribution.
          </p>
        </Link>
      </div>
    </div>
  );
}
