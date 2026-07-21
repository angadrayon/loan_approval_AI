"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { apiClient, ApiError } from "@/lib/api-client";

/**
 * Officer Application Review Page — paginated list of all applications.
 *
 * Requirement 15.2
 */

interface ApplicationEntry {
  id: string;
  user_id: string;
  status: string;
  created_at: string;
  age: number;
  monthly_income: number;
  credit_score: number;
  loan_amount_requested: number;
}

export default function OfficerApplicationsPage() {
  const [applications, setApplications] = useState<ApplicationEntry[]>([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetch() {
      setLoading(true);
      try {
        const result = await apiClient.getReviewApplications(page);
        setApplications(result.data as unknown as ApplicationEntry[]);
        setTotal(result.total);
        setTotalPages(result.total_pages);
      } catch (err) {
        setError(err instanceof ApiError ? err.detail : "Failed to load");
      } finally {
        setLoading(false);
      }
    }
    fetch();
  }, [page]);

  if (loading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      <h1 className="mb-6 text-2xl font-bold tracking-tight text-foreground">Application Review</h1>

      {error && <p className="mb-4 text-sm text-destructive">{error}</p>}

      {applications.length === 0 ? (
        <div className="rounded-lg border border-border bg-card p-8 text-center">
          <p className="text-muted-foreground">No applications submitted yet.</p>
        </div>
      ) : (
        <>
          <div className="overflow-x-auto rounded-lg border border-border">
            <table className="w-full text-sm">
              <thead className="bg-muted/50">
                <tr>
                  <th className="px-4 py-3 text-left font-medium text-muted-foreground">Date</th>
                  <th className="px-4 py-3 text-left font-medium text-muted-foreground">Credit Score</th>
                  <th className="px-4 py-3 text-left font-medium text-muted-foreground">Income</th>
                  <th className="px-4 py-3 text-left font-medium text-muted-foreground">Loan Amount</th>
                  <th className="px-4 py-3 text-left font-medium text-muted-foreground">Status</th>
                  <th className="px-4 py-3 text-left font-medium text-muted-foreground">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {applications.map((app) => (
                  <tr key={app.id} className="hover:bg-accent/30">
                    <td className="px-4 py-3 text-foreground">{new Date(app.created_at).toLocaleDateString()}</td>
                    <td className="px-4 py-3 text-foreground">{app.credit_score}</td>
                    <td className="px-4 py-3 text-foreground">${app.monthly_income?.toLocaleString()}</td>
                    <td className="px-4 py-3 text-foreground">${app.loan_amount_requested?.toLocaleString()}</td>
                    <td className="px-4 py-3">
                      <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                        app.status === "Approved" ? "bg-green-100 text-green-700" :
                        app.status === "Rejected" ? "bg-red-100 text-red-700" :
                        "bg-yellow-100 text-yellow-700"
                      }`}>{app.status}</span>
                    </td>
                    <td className="px-4 py-3">
                      <Link href={`/officer/applications/${app.id}`} className="text-xs font-medium text-primary hover:underline">
                        View Details
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {totalPages > 1 && (
            <div className="mt-4 flex items-center justify-center gap-2">
              <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1} className="min-h-[44px] rounded-md border px-3 py-2 text-sm disabled:opacity-50">Previous</button>
              <span className="text-sm text-muted-foreground">Page {page} of {totalPages} ({total})</span>
              <button onClick={() => setPage((p) => Math.min(totalPages, p + 1))} disabled={page === totalPages} className="min-h-[44px] rounded-md border px-3 py-2 text-sm disabled:opacity-50">Next</button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
