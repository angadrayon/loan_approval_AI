"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";

/**
 * Protected route layout — wraps all protected pages (applicant/*, officer/*, admin/*).
 * First layer of protection: checks authentication only.
 * Individual route groups add role-specific guards via RoleGuard.
 *
 * - If not authenticated → redirect to /login (Requirement 3.7)
 * - If authenticated → render children
 * - Shows loading state while checking auth
 */
export default function ProtectedLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { isAuthenticated, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !isAuthenticated) {
      router.replace("/login");
    }
  }, [isAuthenticated, loading, router]);

  // Show loading spinner while checking auth state
  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    );
  }

  // Not authenticated — redirect is happening, render nothing
  if (!isAuthenticated) {
    return null;
  }

  // Authenticated — render children (role guards applied at sub-layout level)
  return <>{children}</>;
}
