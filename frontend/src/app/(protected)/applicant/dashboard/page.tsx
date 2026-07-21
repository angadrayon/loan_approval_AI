"use client";

import Link from "next/link";
import { useAuth } from "@/hooks/useAuth";

/**
 * Applicant Dashboard — central hub for loan applicants.
 *
 * Provides navigation to: New Assessment, What-If Simulator,
 * Assessment History, and other features.
 *
 * Requirement 14.1
 */
export default function ApplicantDashboard() {
  const { user } = useAuth();

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold tracking-tight text-foreground md:text-3xl">
          Welcome back{user?.email ? `, ${user.email.split("@")[0]}` : ""}
        </h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Manage your loan applications and view your credit assessments.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        {/* New Assessment */}
        <Link
          href="/applicant/apply"
          className="group rounded-lg border border-border bg-card p-6 shadow-sm transition-colors hover:border-primary/50 hover:bg-accent/50"
        >
          <h3 className="text-lg font-semibold text-card-foreground group-hover:text-primary">
            New Assessment
          </h3>
          <p className="mt-2 text-sm text-muted-foreground">
            Submit a loan application and receive an instant credit risk assessment.
          </p>
        </Link>

        {/* Assessment History */}
        <Link
          href="/applicant/history"
          className="group rounded-lg border border-border bg-card p-6 shadow-sm transition-colors hover:border-primary/50 hover:bg-accent/50"
        >
          <h3 className="text-lg font-semibold text-card-foreground group-hover:text-primary">
            Assessment History
          </h3>
          <p className="mt-2 text-sm text-muted-foreground">
            View your previous loan applications and their outcomes.
          </p>
        </Link>

        {/* What-If Simulator */}
        <Link
          href="/applicant/simulator"
          className="group rounded-lg border border-border bg-card p-6 shadow-sm transition-colors hover:border-primary/50 hover:bg-accent/50"
        >
          <h3 className="text-lg font-semibold text-card-foreground group-hover:text-primary">
            What-If Simulator
          </h3>
          <p className="mt-2 text-sm text-muted-foreground">
            Explore how changes to your finances could affect your approval chances.
          </p>
        </Link>
      </div>
    </div>
  );
}
