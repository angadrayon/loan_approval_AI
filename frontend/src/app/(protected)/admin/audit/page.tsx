"use client";

import { useEffect, useState } from "react";
import { apiClient, ApiError } from "@/lib/api-client";

/**
 * Admin Audit Logs Page — paginated, filterable audit trail.
 *
 * Requirement 12.3
 */

interface AuditEntry {
  id: string;
  user_id: string | null;
  event_type: string;
  event_data: Record<string, unknown>;
  ip_address: string | null;
  created_at: string;
}

export default function AuditPage() {
  const [logs, setLogs] = useState<AuditEntry[]>([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetch() {
      setLoading(true);
      try {
        const result = await apiClient.getAuditLogs(page);
        setLogs(result.data as unknown as AuditEntry[]);
        setTotal(result.total);
        setTotalPages(result.total_pages);
      } catch (err) {
        setError(err instanceof ApiError ? err.detail : "Failed to load audit logs");
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
      <h1 className="mb-6 text-2xl font-bold text-foreground">Audit Logs</h1>

      {error && <p className="mb-4 text-sm text-destructive">{error}</p>}

      {logs.length === 0 ? (
        <div className="rounded-lg border border-border bg-card p-8 text-center">
          <p className="text-muted-foreground">No audit logs recorded yet.</p>
        </div>
      ) : (
        <>
          <div className="overflow-x-auto rounded-lg border border-border">
            <table className="w-full text-sm">
              <thead className="bg-muted/50">
                <tr>
                  <th className="px-4 py-3 text-left font-medium text-muted-foreground">Timestamp</th>
                  <th className="px-4 py-3 text-left font-medium text-muted-foreground">Event Type</th>
                  <th className="px-4 py-3 text-left font-medium text-muted-foreground">User</th>
                  <th className="px-4 py-3 text-left font-medium text-muted-foreground">IP</th>
                  <th className="px-4 py-3 text-left font-medium text-muted-foreground">Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {logs.map((log) => (
                  <tr key={log.id} className="hover:bg-accent/30">
                    <td className="px-4 py-3 text-foreground whitespace-nowrap">{new Date(log.created_at).toLocaleString()}</td>
                    <td className="px-4 py-3">
                      <span className="rounded-full bg-muted px-2 py-0.5 text-xs font-medium">{log.event_type}</span>
                    </td>
                    <td className="px-4 py-3 text-muted-foreground text-xs">{log.user_id?.slice(0, 8) || "system"}</td>
                    <td className="px-4 py-3 text-muted-foreground text-xs">{log.ip_address || "—"}</td>
                    <td className="px-4 py-3 text-xs text-muted-foreground max-w-[200px] truncate">
                      {JSON.stringify(log.event_data).slice(0, 80)}...
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
