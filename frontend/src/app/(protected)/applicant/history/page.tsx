"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { apiClient, ApiError } from "@/lib/api-client";

/**
 * Assessment History Page — paginated list of past applications.
 *
 * Shows date, decision, risk score, and approval probability per entry.
 * Sorted by date descending, 20 items per page.
 *
 * Requirements: 14.2, 14.3, 14.4, 14.5
 */

interface ApplicationEntry {
  id: string;
  status: string;
  created_at: string;
  age: number;
  monthly_income: number;
  loan_amount_requested: number;
}

export default function HistoryPage() {
  const [applications, setApplications] = useState<ApplicationEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchHistory() {
      setLoading(true);
      try {
        const result = await apiClient.getApplications(page);
        setApplications(result.data as unknown as ApplicationEntry[]);
        setTotal(result.total);
        setTotalPages(result.total_pages);
      } catch (err) {
        if (err instanceof ApiError) {
          setError(err.detail);
        } else {
          setError("Failed to load history");
        }
      } finally {
        setLoading(false);
      }
    }
    fetchHistory();
  }, [page]);

  if (loading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-8">
        <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-6 text-center">
          <p className="text-sm text-destructive">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold tracking-tight text-foreground">Assessment History</h1>
        <Link
          href="/applicant/apply"
          className="inline-flex min-h-[44px] items-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
        >
          New Assessment
        </Link>
      </div>

      {applications.length === 0 ? (
        <div className="rounded-lg border border-border bg-card p-8 text-center">
          <p className="text-muted-foreground">No assessments yet.</p>
          <Link href="/applicant/apply" className="mt-3 inline-block text-sm font-medium text-primary hover:underline">
            Submit your first application →
          </Link>
        </div>
      ) : (
        <>
          <div className="space-y-3">
            {applications.map((app) => (
              <Link
                key={app.id}
                href={`/applicant/assessment/${app.id}`}
                className="block rounded-lg border border-border bg-card p-4 transition-colors hover:border-primary/50 hover:bg-accent/30"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-foreground">
                      Loan: ${app.loan_amount_requested?.toLocaleString() || "—"}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {new Date(app.created_at).toLocaleDateString()} · Income: ${app.monthly_income?.toLocaleString() || "—"}
                    </p>
                  </div>
                  <span
                    className={`rounded-full px-3 py-1 text-xs font-medium ${
                      app.status === "Approved"
                        ? "bg-green-100 text-green-700"
                        : app.status === "Rejected"
                        ? "bg-red-100 text-red-700"
                        : "bg-yellow-100 text-yellow-700"
                    }`}
                  >
                    {app.status}
                  </span>
                </div>
              </Link>
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="mt-6 flex items-center justify-center gap-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="min-h-[44px] rounded-md border border-border px-3 py-2 text-sm disabled:opacity-50"
              >
                Previous
              </button>
              <span className="text-sm text-muted-foreground">
                Page {page} of {totalPages} ({total} total)
              </span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="min-h-[44px] rounded-md border border-border px-3 py-2 text-sm disabled:opacity-50"
              >
                Next
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
