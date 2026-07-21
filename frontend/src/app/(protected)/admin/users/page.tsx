"use client";

import { useEffect, useState } from "react";
import { apiClient, ApiError } from "@/lib/api-client";

/**
 * Admin User Management Page.
 *
 * Paginated user list with role management.
 * Requirements: 16.2, 16.3, 16.4, 16.5, 16.6
 */

interface UserEntry {
  id: string;
  user_id: string;
  name: string;
  role: string;
  created_at: string;
}

const ROLES = ["Applicant", "Bank_Officer", "Admin"];

export default function UsersPage() {
  const [users, setUsers] = useState<UserEntry[]>([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [changingRole, setChangingRole] = useState<string | null>(null);

  useEffect(() => {
    fetchUsers();
  }, [page]);

  async function fetchUsers() {
    setLoading(true);
    try {
      const result = await apiClient.getUsers(page);
      setUsers(result.data as unknown as UserEntry[]);
      setTotal(result.total);
      setTotalPages(result.total_pages);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Failed to load users");
    } finally {
      setLoading(false);
    }
  }

  async function handleRoleChange(userId: string, currentRole: string, newRole: string) {
    if (newRole === currentRole) return;

    const user = users.find((u) => u.user_id === userId);
    const confirmed = window.confirm(
      `Change ${user?.name || "user"}'s role from "${currentRole}" to "${newRole}"?`
    );
    if (!confirmed) return;

    setChangingRole(userId);
    setActionError(null);

    try {
      await apiClient.updateUserRole(userId, newRole);
      // Refresh list
      await fetchUsers();
    } catch (err) {
      if (err instanceof ApiError) {
        setActionError(err.detail);
      } else {
        setActionError("Failed to update role");
      }
    } finally {
      setChangingRole(null);
    }
  }

  if (loading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      <h1 className="mb-6 text-2xl font-bold text-foreground">User Management</h1>

      {error && <p className="mb-4 text-sm text-destructive">{error}</p>}
      {actionError && (
        <div className="mb-4 rounded-md border border-destructive/50 bg-destructive/10 p-3 text-sm text-destructive">
          {actionError}
        </div>
      )}

      {users.length === 0 ? (
        <div className="rounded-lg border border-border bg-card p-8 text-center">
          <p className="text-muted-foreground">No users registered yet.</p>
        </div>
      ) : (
        <>
          <div className="overflow-x-auto rounded-lg border border-border">
            <table className="w-full text-sm">
              <thead className="bg-muted/50">
                <tr>
                  <th className="px-4 py-3 text-left font-medium text-muted-foreground">Name</th>
                  <th className="px-4 py-3 text-left font-medium text-muted-foreground">Registered</th>
                  <th className="px-4 py-3 text-left font-medium text-muted-foreground">Role</th>
                  <th className="px-4 py-3 text-left font-medium text-muted-foreground">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {users.map((user) => (
                  <tr key={user.id} className="hover:bg-accent/30">
                    <td className="px-4 py-3">
                      <p className="font-medium text-foreground">{user.name}</p>
                      <p className="text-xs text-muted-foreground">{user.user_id.slice(0, 8)}...</p>
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">
                      {new Date(user.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                        user.role === "Admin" ? "bg-purple-100 text-purple-700" :
                        user.role === "Bank_Officer" ? "bg-blue-100 text-blue-700" :
                        "bg-gray-100 text-gray-700"
                      }`}>{user.role}</span>
                    </td>
                    <td className="px-4 py-3">
                      <select
                        value={user.role}
                        onChange={(e) => handleRoleChange(user.user_id, user.role, e.target.value)}
                        disabled={changingRole === user.user_id}
                        className="min-h-[36px] rounded-md border border-input bg-background px-2 py-1 text-xs disabled:opacity-50"
                      >
                        {ROLES.map((r) => (
                          <option key={r} value={r}>{r}</option>
                        ))}
                      </select>
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
