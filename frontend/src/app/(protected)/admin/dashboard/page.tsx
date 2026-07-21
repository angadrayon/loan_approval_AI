"use client";

import Link from "next/link";

/**
 * Admin Dashboard — monitoring hub for system health, fairness, and user management.
 *
 * Provides navigation to: Fairness Monitoring, User Management,
 * Audit Logs, and Model Statistics.
 *
 * Requirement 16.1
 */
export default function AdminDashboard() {
  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold tracking-tight text-foreground md:text-3xl">
          Admin Dashboard
        </h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Monitor system health, fairness metrics, and manage users.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <Link
          href="/admin/fairness"
          className="group rounded-lg border border-border bg-card p-6 shadow-sm transition-colors hover:border-primary/50 hover:bg-accent/50"
        >
          <h3 className="text-lg font-semibold text-card-foreground group-hover:text-primary">
            Fairness Monitoring
          </h3>
          <p className="mt-2 text-sm text-muted-foreground">
            View demographic parity, equalized odds, and proxy bias metrics.
          </p>
        </Link>

        <Link
          href="/admin/users"
          className="group rounded-lg border border-border bg-card p-6 shadow-sm transition-colors hover:border-primary/50 hover:bg-accent/50"
        >
          <h3 className="text-lg font-semibold text-card-foreground group-hover:text-primary">
            User Management
          </h3>
          <p className="mt-2 text-sm text-muted-foreground">
            View registered users and manage role assignments.
          </p>
        </Link>

        <Link
          href="/admin/audit"
          className="group rounded-lg border border-border bg-card p-6 shadow-sm transition-colors hover:border-primary/50 hover:bg-accent/50"
        >
          <h3 className="text-lg font-semibold text-card-foreground group-hover:text-primary">
            Audit Logs
          </h3>
          <p className="mt-2 text-sm text-muted-foreground">
            View system audit trail for compliance and traceability.
          </p>
        </Link>

        <Link
          href="/admin/models"
          className="group rounded-lg border border-border bg-card p-6 shadow-sm transition-colors hover:border-primary/50 hover:bg-accent/50"
        >
          <h3 className="text-lg font-semibold text-card-foreground group-hover:text-primary">
            Model Statistics
          </h3>
          <p className="mt-2 text-sm text-muted-foreground">
            Compare XGBoost and Random Forest performance metrics.
          </p>
        </Link>
      </div>
    </div>
  );
}
