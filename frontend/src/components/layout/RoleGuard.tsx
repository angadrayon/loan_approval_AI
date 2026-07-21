"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import type { UserRole } from "@/types";

interface RoleGuardProps {
  allowedRoles: UserRole[];
  children: React.ReactNode;
}

/**
 * Returns the role-appropriate dashboard path for a given user role.
 */
function getDashboardPath(role: UserRole): string {
  switch (role) {
    case "Bank_Officer":
      return "/officer/dashboard";
    case "Admin":
      return "/admin/dashboard";
    case "Applicant":
    default:
      return "/applicant/dashboard";
  }
}

/**
 * RoleGuard component — enforces role-based access control on protected routes.
 *
 * - While loading: shows a loading spinner
 * - If not authenticated: redirects to /login
 * - If authenticated but role not in allowedRoles:
 *   - Shows a 5-second "Access Denied" notification
 *   - Redirects to the user's role-appropriate dashboard after 500ms
 * - If authenticated and authorized: renders children
 *
 * Requirements: 3.2, 3.3, 3.4, 3.5, 3.7
 */
export function RoleGuard({ allowedRoles, children }: RoleGuardProps) {
  const { isAuthenticated, role, loading } = useAuth();
  const router = useRouter();
  const [accessDenied, setAccessDenied] = useState(false);

  useEffect(() => {
    if (loading) return;

    // Requirement 3.7: Unauthenticated → redirect to login
    if (!isAuthenticated) {
      router.replace("/login");
      return;
    }

    // Requirement 3.5: Unauthorized → show access denied notification for 5 seconds,
    // then redirect to role-appropriate dashboard
    if (role && !allowedRoles.includes(role)) {
      setAccessDenied(true);

      // Redirect after 5 seconds so user sees the full notification
      const redirectTimer = setTimeout(() => {
        router.replace(getDashboardPath(role));
      }, 5000);

      return () => {
        clearTimeout(redirectTimer);
      };
    }
  }, [isAuthenticated, role, loading, allowedRoles, router]);

  // Loading state
  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    );
  }

  // Not authenticated — redirect is happening
  if (!isAuthenticated) {
    return null;
  }

  // Access denied notification + redirect in progress
  if (accessDenied) {
    return (
      <div className="relative min-h-screen bg-background">
        <div
          role="alert"
          className="fixed left-0 right-0 top-0 z-50 flex items-center justify-center bg-destructive px-4 py-3 text-destructive-foreground shadow-lg"
        >
          <p className="text-sm font-medium">
            Access Denied — You don&apos;t have permission to view this page
          </p>
        </div>
      </div>
    );
  }

  // Authorized — role not yet loaded (edge case)
  if (!role || !allowedRoles.includes(role)) {
    return null;
  }

  // Authorized — render children
  return <>{children}</>;
}
